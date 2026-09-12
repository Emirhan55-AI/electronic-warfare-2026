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
BW_THRESHOLD_DB = 6.0
CHANNEL_BW = 100e3
WINDOW_BINS = 180          # ~47 kHz'lik pencere - gercek sinyal genisligini yakalamak icin


def measure_bandwidth(power_db, peak_idx, freq_per_bin, threshold_db=BW_THRESHOLD_DB):
    peak_val = power_db[peak_idx]
    thresh = peak_val - threshold_db
    n = len(power_db)
    lo = peak_idx
    while lo > 0 and power_db[lo] > thresh:
        lo -= 1
    hi = peak_idx
    while hi < n - 1 and power_db[hi] > thresh:
        hi += 1
    return (hi - lo) * freq_per_bin


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
    bw_hz = measure_bandwidth(power_db_all, int(round(centroid_idx)), freq_per_bin)

    return (margin > MARGIN_DB), margin, cfo_hz, bw_hz


def channelize(chunk, cfo_hz):
    n = np.arange(len(chunk))
    mixer = np.exp(-1j * 2 * np.pi * cfo_hz * n / RX_SAMPLE_RATE)
    shifted = chunk * mixer
    taps = firwin(127, CHANNEL_BW / 2, fs=RX_SAMPLE_RATE)
    return lfilter(taps, 1.0, shifted)


def spectrum_metrics(x):
    N = min(len(x), FFT_SIZE * 8)
    seg = x[:N]
    win = np.hanning(N)
    spec = np.fft.fftshift(np.fft.fft(seg * win))
    power_db = 20 * np.log10(np.abs(spec) + 1e-12)
    noise_floor = np.median(power_db)
    peak = np.max(power_db)
    return peak, noise_floor, peak - noise_floor


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

            is_signal, wb_margin, cfo_hz, bw_hz = wideband_detect(chunk)
            if not is_signal:
                print(f"[genis bant] margin={wb_margin:5.1f} dB -> NO-SIGNAL")
                continue

            filtered = channelize(chunk, cfo_hz)
            settle = 200
            core = filtered[settle:-settle] if len(filtered) > 2*settle else filtered
            peak, noise, ch_margin = spectrum_metrics(core)
            est_freq = RX_CENTER_FREQ + cfo_hz

            print(f"[genis bant] margin={wb_margin:5.1f} dB  BW~{bw_hz/1e3:5.2f} kHz -> SIGNAL @ {est_freq/1e6:.4f} MHz  |  "
                  f"[filtre sonrasi] margin={ch_margin:5.1f} dB")


if __name__ == "__main__":
    main()
