import numpy as np
from scipy.signal import upfirdn
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

FS = 2e6
N_SAMPLES = 40000


def rrc_taps(beta, sps, span):
    N = span * sps
    t = np.arange(-N, N + 1) / sps
    h = np.zeros_like(t)
    for i, ti in enumerate(t):
        if ti == 0.0:
            h[i] = 1.0 - beta + 4 * beta / np.pi
        elif beta != 0 and abs(abs(4 * beta * ti) - 1.0) < 1e-8:
            h[i] = (beta / np.sqrt(2)) * (
                (1 + 2 / np.pi) * np.sin(np.pi / (4 * beta)) +
                (1 - 2 / np.pi) * np.cos(np.pi / (4 * beta))
            )
        else:
            num = np.sin(np.pi * ti * (1 - beta)) + 4 * beta * ti * np.cos(np.pi * ti * (1 + beta))
            den = np.pi * ti * (1 - (4 * beta * ti) ** 2)
            h[i] = num / den
    h = h / np.sqrt(np.sum(h ** 2))
    return h


def gen_am(n_samples, fs, rng):
    f_mod = rng.uniform(300, 4000)
    depth = rng.uniform(0.3, 0.95)
    cfo_residual = rng.uniform(-5000, 5000)
    t = np.arange(n_samples) / fs
    msg = np.cos(2 * np.pi * f_mod * t)
    if rng.random() < 0.5:
        f_mod2 = rng.uniform(300, 4000)
        msg = 0.6 * msg + 0.4 * np.cos(2 * np.pi * f_mod2 * t)
        msg = msg / (np.max(np.abs(msg)) + 1e-12)
    envelope = 1.0 + depth * msg
    carrier = np.exp(1j * 2 * np.pi * cfo_residual * t)
    return envelope * carrier


def gen_fm(n_samples, fs, rng):
    f_mod = rng.uniform(300, 4000)
    dev = rng.uniform(10000, 100000)
    cfo_residual = rng.uniform(-5000, 5000)
    t = np.arange(n_samples) / fs
    phase = 2 * np.pi * cfo_residual * t + (dev / f_mod) * np.sin(2 * np.pi * f_mod * t)
    return np.exp(1j * phase)


def gen_psk(n_samples, fs, rng, order=2):
    symbol_rate = rng.uniform(50e3, 500e3)
    sps = max(int(fs / symbol_rate), 2)
    excess_bw = rng.uniform(0.2, 0.5)
    cfo_residual = rng.uniform(-5000, 5000)
    num_symbols = int(n_samples / sps) + 60
    bits = rng.integers(0, order, num_symbols)
    if order == 2:
        symbols = (2 * bits - 1).astype(np.complex128)
    else:
        angles = (2 * np.pi * bits / order) + np.pi / 4
        symbols = np.exp(1j * angles)
    taps = rrc_taps(excess_bw, sps, span=6)
    baseband = upfirdn(taps, symbols, up=sps)
    trim = len(taps)
    avail = len(baseband) - trim
    if avail >= n_samples:
        baseband = baseband[trim:trim + n_samples]
    else:
        baseband = np.pad(baseband[trim:], (0, n_samples - avail))
    n = np.arange(len(baseband))
    carrier = np.exp(1j * 2 * np.pi * cfo_residual * n / fs)
    return (baseband * carrier)[:n_samples]


def add_noise(sig, snr_db, rng):
    sig_power = np.mean(np.abs(sig) ** 2)
    noise_power = sig_power / (10 ** (snr_db / 10))
    noise = (rng.standard_normal(len(sig)) + 1j * rng.standard_normal(len(sig))) * np.sqrt(noise_power / 2)
    return sig + noise


def kurtosis(v):
    v = v - np.mean(v)
    m2 = np.mean(v ** 2)
    m4 = np.mean(v ** 4)
    return m4 / (m2 ** 2 + 1e-12)


def extract_features(x, fs):
    x = x - np.mean(x)
    power = np.mean(np.abs(x) ** 2)
    if power > 1e-20:
        x = x / np.sqrt(power)

    amp = np.abs(x)
    phase = np.unwrap(np.angle(x))
    freq = np.diff(phase) * fs / (2 * np.pi)

    amp_mean = np.mean(amp) + 1e-12
    amp_n = amp / amp_mean - 1.0

    std_amp = float(np.std(amp_n))
    kurt_amp = float(kurtosis(amp_n))
    std_freq = float(np.std(freq))
    kurt_freq = float(kurtosis(freq))

    spec = np.abs(np.fft.fft(amp_n)) ** 2
    gamma_max = float(np.max(spec) / (np.sum(spec) + 1e-12))

    M20 = np.mean(x ** 2)
    M21 = np.mean(x * np.conj(x))
    M42 = np.mean(np.abs(x) ** 4)
    C42 = M42 - np.abs(M20) ** 2 - 2 * M21.real ** 2
    abs_C42 = float(np.abs(C42))

    return [std_amp, kurt_amp, std_freq, kurt_freq, gamma_max, abs_C42]


def build_dataset(n_per_class, seed=42):
    rng = np.random.default_rng(seed)
    X, y, tags = [], [], []

    generators = [
        ("AM", lambda: gen_am(N_SAMPLES, FS, rng), 0),
        ("FM", lambda: gen_fm(N_SAMPLES, FS, rng), 0),
        ("BPSK", lambda: gen_psk(N_SAMPLES, FS, rng, order=2), 1),
        ("QPSK", lambda: gen_psk(N_SAMPLES, FS, rng, order=4), 1),
    ]

    for name, gen_fn, label in generators:
        for _ in range(n_per_class):
            snr = rng.uniform(4, 30)
            sig = gen_fn()
            sig = add_noise(sig, snr, rng)
            X.append(extract_features(sig, FS))
            y.append(label)
            tags.append(name)

    return np.array(X), np.array(y), np.array(tags)


if __name__ == "__main__":
    print("Sentetik veri uretiliyor...")
    X, y, tags = build_dataset(n_per_class=500)
    print(f"Toplam ornek: {len(y)}  (ANALOG={np.sum(y==0)}, DIGITAL={np.sum(y==1)})")

    X_train, X_test, y_train, y_test, tags_train, tags_test = train_test_split(
        X, y, tags, test_size=0.25, random_state=0, stratify=y
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    clf = LogisticRegression(max_iter=2000)
    clf.fit(X_train_s, y_train)

    y_pred = clf.predict(X_test_s)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nTest dogruluk: {acc*100:.2f}%")
    print("\nKarisiklik matrisi (satir=gercek, sutun=tahmin) [ANALOG, DIGITAL]:")
    print(confusion_matrix(y_test, y_pred))
    print("\nSinif bazinda rapor:")
    print(classification_report(y_test, y_pred, target_names=["ANALOG", "DIGITAL"]))

    print("\nAlt-tip bazinda dogruluk (test seti):")
    for name in ["AM", "FM", "BPSK", "QPSK"]:
        mask = tags_test == name
        if mask.sum() > 0:
            sub_acc = accuracy_score(y_test[mask], y_pred[mask])
            print(f"  {name:6s}: {sub_acc*100:.1f}%  (n={mask.sum()})")

    feature_names = ["std_amp", "kurt_amp", "std_freq", "kurt_freq", "gamma_max", "abs_C42"]
    print("\n--- Dagitim icin parametreler (panel scriptine gomulecek) ---")
    print("FEATURE_ORDER =", feature_names)
    print("SCALER_MEAN =", list(scaler.mean_))
    print("SCALER_SCALE =", list(scaler.scale_))
    print("CLF_COEF =", list(clf.coef_[0]))
    print("CLF_INTERCEPT =", float(clf.intercept_[0]))
