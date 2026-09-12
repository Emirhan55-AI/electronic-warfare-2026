"""
classifier_model.py
--------------------
Sentetik veriyle (AM/FM=ANALOG, BPSK/QPSK=DIGITAL) egitilmis Logistic Regression
siniflandiricinin agirliklari. sklearn GEREKMEZ -- sadece numpy ile calisir,
bu yuzden panel.py icinde dogrudan import edilip kullanilabilir.

Test dogrulugu (sentetik veri, 25% test split, n=2000): %97.4
  ANALOG precision=1.00 recall=0.95 | DIGITAL precision=0.95 recall=1.00
  Alt-tip: AM %98.4  FM %91.1  BPSK %100.0  QPSK %100.0

extract_features() (feature_extractor_v1.py) ciktisiyla BIREBIR AYNI SIRADA
kullanilmalidir: [std_amp, kurt_amp, std_freq, kurt_freq, gamma_max, abs_C42]
"""

import numpy as np

FEATURE_ORDER = ['std_amp', 'kurt_amp', 'std_freq', 'kurt_freq', 'gamma_max', 'abs_C42']

SCALER_MEAN = np.array([
    0.31119843325815594,
    2.887608560439343,
    154119.00366248112,
    10.702285652971021,
    0.0921426674813463,
    0.6729956263673207,
])

SCALER_SCALE = np.array([
    0.1368327388717661,
    0.7343810534134055,
    92776.07556256253,
    13.213337573318785,
    0.11697074299120157,
    0.2127352986740481,
])

CLF_COEF = np.array([
    3.6711185513981417,
    2.0717566698178715,
    3.681348938034644,
    2.491256457487009,
    -3.1586049885490883,
    2.7406800702081395,
])

CLF_INTERCEPT = -2.166351307239169


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def classify(features):
    """
    features: feature_extractor_v1.extract_features() ciktisi olan dict,
              veya FEATURE_ORDER sirasinda bir liste/array.

    Donus: (label:str "ANALOG"/"DIGITAL", prob_digital:float, feat_vector:list)
    """
    if isinstance(features, dict):
        vec = np.array([features[k] for k in FEATURE_ORDER], dtype=float)
    else:
        vec = np.array(features, dtype=float)

    vec_scaled = (vec - SCALER_MEAN) / SCALER_SCALE
    z = np.dot(CLF_COEF, vec_scaled) + CLF_INTERCEPT
    prob_digital = float(_sigmoid(z))
    label = "DIGITAL" if prob_digital >= 0.5 else "ANALOG"
    return label, prob_digital, vec.tolist()


if __name__ == "__main__":
    # hizli kontrol
    test_feat = {
        "std_amp": 0.015, "kurt_amp": 2.9, "std_freq": 14600.0,
        "kurt_freq": 3.3, "gamma_max": 0.05, "abs_C42": 0.999,
    }
    print(classify(test_feat))  # ANALOG bekleniyor (CW benzeri)
