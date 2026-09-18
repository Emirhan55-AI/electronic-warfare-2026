"""16 karelik PL güç hesabının bağımsız NumPy OBW başvuru modeli.

Dört bitişik grup bırakma tanısı her seferinde gözlemin dörtte birini çıkarır;
tek kare bırakıp belirsizliği yapay olarak küçültmez. Ürün PC geri dönüşü değildir.
"""
import math
import numpy as np


def extended_temporal_limit(lower_edge, upper_edge):
    """16 karede genişliğe ölçeklenen, en az yedi hücrelik kenar kapısı."""
    width = float(upper_edge) - float(lower_edge)
    if not math.isfinite(width) or width <= 0:
        raise ValueError("Geçerli OBW kenarları gerekir.")
    return max(7.0, 0.05 * width)


def extended_obw_reference(psd, lower, upper):
    values = np.asarray(psd, dtype=float)
    if values.shape != (16, 4096) or not np.all(np.isfinite(values)) or np.any(values < 0):
        raise ValueError("16 sonlu, negatif olmayan güç karesi gerekir.")
    if not 56 <= lower <= upper <= 4039 or upper - lower + 1 < 8:
        raise ValueError("Analiz aralığı geçersiz.")
    kernel = np.array([.25, .5, .25])

    def edge_result(frames):
        average = frames.mean(axis=0)
        left = average[lower - 36:lower - 4].mean()
        right = average[upper + 5:upper + 37].mean()
        noise = (left + right) / 2
        weights = np.maximum(np.convolve(average[lower:upper + 1] - noise, kernel, 'same')
                             - 2.5 * noise / math.sqrt(len(frames)) * math.sqrt(.375), 0)
        cumulative = np.cumsum(weights)
        if cumulative[-1] <= 0:
            raise ValueError("Pozitif bant enerjisi yok.")
        def edge(q):
            target = q * cumulative[-1]
            i = min(int(np.searchsorted(cumulative, target)), len(weights) - 1)
            before = cumulative[i - 1] if i else 0
            return lower + i - .5 + (target - before) / max(weights[i], np.finfo(float).tiny)
        return np.array([edge(.0075), edge(.9925)])

    aggregate = edge_result(values)
    subsets = np.array([edge_result(np.delete(values, np.s_[i * 4:(i + 1) * 4], axis=0)) for i in range(4)])
    deviation = float(np.max(np.median(np.abs(subsets - aggregate), axis=0)))
    try:
        groups = np.array([edge_result(values[i * 4:(i + 1) * 4]) for i in range(4)])
        deviation = max(deviation, float(np.max(np.abs(groups - aggregate))))
    except ValueError:
        deviation = 4096.0
    edges = aggregate + np.array([-.375, .375])
    clipped = edges[0] <= lower + .5 or edges[1] >= upper - .5
    temporal_limit = extended_temporal_limit(*edges)
    return {"lower_bin": float(edges[0]), "upper_bin": float(edges[1]),
            "temporal_edge_range_bins": deviation,
            "temporal_edge_limit_bins": temporal_limit,
            "reason": "span_edge_clipping" if clipped else "obw_temporal_instability" if deviation > temporal_limit else None}
