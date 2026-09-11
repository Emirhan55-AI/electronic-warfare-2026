"""KTR-4.2-F1: uzun RF kanalını dondurulmuş ağaçlara bağlayan PC adayı.

Özellik sırası eski modelle aynıdır. Gözlem süresi, FIR ve frekans düzeltmesi
değiştiği için özellik dağılımı aynı kabul edilmez; yeniden RF doğrulaması
gerekir. Ağaç oyları kalibre olasılık veya fiziksel kabul değildir.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .refined_candidate import _entropy, _stats


MODEL_SHA256 = 'afa2872c6363d25e5322b6c382db32a0b9ec3d85260ef4b6ce37d9606ebc67c9'
PROFILE = 'rf-channel-frozen-forest-v1'


def load_frozen_model(path):
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != MODEL_SHA256:
        raise ValueError('Dondurulmuş sınıflandırıcı özeti eşleşmiyor.')
    model = json.loads(data)
    if model['threshold'] != .9:
        raise ValueError('Sabit karar eşiği değişmiş.')
    return model


def _vector(channel, weights, line_share):
    z = channel / np.sqrt(np.mean(abs(channel) ** 2))
    amp = abs(z)
    phase = np.angle(z[1:] * z[:-1].conj())
    values = [float(np.std(amp) / max(np.mean(amp), 1e-12)),
        float(np.mean(amp < .25)), float(np.mean(amp ** 4)),
        float(abs(np.mean(z * z))), float(abs(np.mean(z ** 4))),
        float(line_share), float(np.std(phase)), float(np.mean(abs(phase) > 1)),
        *_stats(amp), *_stats(phase), _entropy(weights),
        float(abs(np.mean(z)) / max(np.mean(abs(z)), 1e-20))]
    a, b = amp - np.mean(amp), phase - np.mean(phase)
    for lag in (1, 2, 4, 8):
        values.extend([float(np.mean(a[lag:] * a[:-lag]) / max(np.mean(a * a), 1e-20)),
                       float(np.mean(b[lag:] * b[:-lag]) / max(np.mean(b * b), 1e-20))])
    vector = np.asarray(values, dtype=np.float32)
    if vector.shape != (26,) or not np.all(np.isfinite(vector)):
        raise ValueError('Sınıflandırma için 26 sonlu özellik gerekli.')
    return vector


def _score(vector, model):
    votes = np.zeros(len(model['classes']))
    for tree in model['trees']:
        node = 0
        for _ in range(len(tree['left'])):
            if tree['left'][node] < 0:
                values = np.asarray(tree['value'][node], dtype=float)
                votes += values / max(float(values.sum()), 1e-30)
                break
            node = (tree['left'][node] if vector[tree['feature'][node]] <= tree['threshold'][node]
                    else tree['right'][node])
        else:
            raise ValueError('Geçersiz sınıflandırıcı ağacı.')
    votes /= len(model['trees'])
    scores = {label: float(score) for label, score in zip(model['classes'], votes)}
    analog = sum(scores.get(c, 0) for c in ('AM', 'NFM'))
    digital = sum(scores.get(c, 0) for c in ('OOK', 'FSK', 'BPSK', 'QPSK', 'QAM'))
    label = 'Analog' if analog >= model['threshold'] else 'Sayısal' if digital >= model['threshold'] else 'Belirsiz'
    return {'decision': label, 'analog_vote': analog, 'digital_vote': digital,
            'family_votes': scores, 'features': vector.tolist()}


def classify_channel(channel, corrected_channel, weights, model):
    """Aile etiketi almadan aynı kanalın düzeltme öncesi/sonrası kararını üret."""
    weights = np.asarray(weights, dtype=float)
    if not len(weights) or weights.sum() <= 0:
        return 'Belirsiz', {'profile': PROFILE, 'reason': 'no_spectral_support'}
    peak = int(np.argmax(weights))
    line_share = float(weights[max(0, peak - 2):peak + 3].sum() / weights.sum())
    before = _score(_vector(channel, weights, line_share), model)
    after = _score(_vector(corrected_channel, weights, line_share), model)
    return after['decision'], {'profile': PROFILE, 'threshold': model['threshold'],
        'model_sha256': MODEL_SHA256, 'before_frequency_correction': before,
        'after_frequency_correction': after, 'physical_acceptance': False,
        'product_acceptance': False, 'votes_are_calibrated_probabilities': False}
