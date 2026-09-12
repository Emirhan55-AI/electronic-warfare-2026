import zmq
import numpy as np
from scipy.signal import firwin, lfilter

ZMQ_ADDR = "tcp://127.0.0.1:5555"
RX_SAMPLE_RATE = 2e6
RX_CENTER_FREQ = 435e6

BLOCK_SAMPLES = 1024 * 50
FFT_SIZE = 1024
DC_EXCLUDE_BINS = 5
MARGIN_DB = 5.0
CHANNEL_BW = 400e3
WINDOW_BINS = 180


def wideband_detect(chunk):
    n_fft_frames = len(chunk) // FFT_SIZE
    window = np.hanning(FFT_SIZE)
    center = FFT_SIZE // 2
    power_accum = np.zeros(FFT_SIZE)
    for i in range(n_fft_frames):
        seg = chunk[i*FFT_SIZE:(i+1)*FFT_SIZE]
        spec = np.fft.fftshift(np.fft.fft(seg * window))
        power_accum += np.abs(spec) ** 2
    avg_power = power_accum / n_fft_frames

    masked_power = avg_power.copy()
    masked_power[center - DC_EXCLUDE_BINS: center + DC_EXCLUDE_BINS + 1] = 0.0

    power_db_all = 10 * np.log10(avg_power + 1e-20)
    valid_db = power_db_all.copy()
    valid_db[center - DC_EXCLUDE_BINS: center + DC_EXCLUDE_BINS + 1] = np.nan
    noise_floor = np.nanmedian(valid_db)

    cumsum = np.cumsum(np.insert(masked_power, 0, 0.0))
    window_sums = cumsum[WINDOW_BINS:] - cumsum[:-WINDOW_BINS]
    best_start = int(np.argmax(window_sums))
    best_avg_power = window_sums[best_start] / WINDOW_BINS
    peak_db = 10 * np.log10(best_avg_power + 1e-20)
    margin = peak_db - noise_floor

    idxs = np.arange(best_start, best_start + WINDOW_BINS)
    weights = masked_power[idxs]
    if weights.sum() > 0:
        centroid_idx = float(np.sum(idxs * weights) / weights.sum())
    else:
        centroid_idx = best_start + WINDOW_BINS / 2

    freq_per_bin = RX_SAMPLE_RATE / FFT_SIZE
    cfo_hz = (centroid_idx - center) * freq_per_bin

    return (margin > MARGIN_DB), margin, cfo_hz


def channelize(chunk, cfo_hz):
    n = np.arange(len(chunk))
    mixer = np.exp(-1j * 2 * np.pi * cfo_hz * n / RX_SAMPLE_RATE)
    shifted = chunk * mixer
    taps = firwin(127, CHANNEL_BW / 2, fs=RX_SAMPLE_RATE)
    return lfilter(taps, 1.0, shifted)


def normalize_iq(x):
    x = x - np.mean(x)
    power = np.mean(np.abs(x) ** 2)
    if power < 1e-20:
        return x
    return x / np.sqrt(power)


def kurtosis(v):
    v = v - np.mean(v)
    m2 = np.mean(v ** 2)
    m4 = np.mean(v ** 4)
    return m4 / (m2 ** 2 + 1e-12)


def extract_features(x, fs):
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

    return {
        "std_amp": std_amp,
        "kurt_amp": kurt_amp,
        "std_freq": std_freq,
        "kurt_freq": kurt_freq,
        "gamma_max": gamma_max,
        "abs_C42": abs_C42,
    }


def main():
    ctx = zmq.Context()
    sock = ctx.socket(zmq.SUB)
    sock.connect(ZMQ_ADDR)
    sock.setsockopt(zmq.SUBSCRIBE, b"")
    sock.setsockopt(zmq.RCVTIMEO, 2000)
    print(f"ZMQ SUB baglandi: {ZMQ_ADDR}\n")

    buf = np.array([], dtype=np.complex64)
    while True:
        try:
            msg = sock.recv()
        except zmq.error.Again:
            print("... veri gelmiyor")
            continue
        samples = np.frombuffer(msg, dtype=np.complex64)
        buf = np.concatenate([buf, samples])

        while buf.size >= BLOCK_SAMPLES:
            chunk = buf[:BLOCK_SAMPLES]
            buf = buf[BLOCK_SAMPLES:]

            is_signal, margin, cfo_hz = wideband_detect(chunk)
            if not is_signal:
                print(f"margin={margin:5.1f} dB -> NO-SIGNAL")
                continue

            filtered = channelize(chunk, cfo_hz)
            settle = 200
            core = filtered[settle:-settle] if len(filtered) > 2 * settle else filtered

            norm = normalize_iq(core)
            feats = extract_features(norm, RX_SAMPLE_RATE)

            print(f"margin={margin:5.1f} dB  CFO={RX_CENTER_FREQ+cfo_hz:.4f}  "
                  f"std_amp={feats['std_amp']:.3f}  kurt_amp={feats['kurt_amp']:.2f}  "
                  f"std_freq={feats['std_freq']:.1f}  kurt_freq={feats['kurt_freq']:.2f}  "
                  f"gamma_max={feats['gamma_max']:.3f}  abs_C42={feats['abs_C42']:.3f}")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
