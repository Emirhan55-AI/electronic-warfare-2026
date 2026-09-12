"""
gen_signal.py
-------------
Panel'in "TX" tarafi. Kullanici "AM" / "FM" / "BPSK" / "QPSK" yazdiginda
bu script gercek donanima (hackrf_transfer) verilecek int8 IQ dosyasini
uretir ve hangi merkez frekans / TX gain ile gonderilmesi gerektigini
(rastgele secilmis olarak) geri doner.

ONEMLI - FREKANS MIMARISI (bir onceki versiyondaki hatanin duzeltilmesi):
Once TX'in MUTLAK frekansini (435.1-435.5MHz) HEM DE dosya icindeki artik
tasiyici ofsetini (cfo, +-150kHz) AYRI AYRI rastgele seciyordum. Bu ikisi
ust uste binince toplam ofset, daha once gercek donanimda dogrulanmis
~300kHz'lik guvenli bolgenin disina (bazen DC'ye cok yakina) kayabiliyordu
-- bu da RX tarafinin yanlis/zayif bir spektral bilesene kilitlenmesine
(dusuk marj, anlamsiz ozellikler) yol acti.

Duzeltme: TX'in mutlak frekansi artik SABIT (RX_CENTER_FREQ ile ayni,
435.0 MHz) -- boylece iki ayri rastgele katman cakismiyor. Rastgelelik
TEK bir yerden, dosya icindeki artik tasiyici ofsetinden (cfo) geliyor;
bu deger TUM modulasyon tipleri icin AYNI dagilimdan (250-350 kHz,
daha once dogrulanan ~300kHz bolgesi civarinda) rastgele secilir --
yani sinifa gore degil, hepsine ayni sekilde uygulanir, dolayisiyla
"sinif sabit bir frekansa baglanmasin" kuralini ihlal etmez (sabit bir
TX merkez frekansi da bu kurali ihlal etmez, cunku TUM siniflar icin
AYNI sabit deger -- yani sinifla ilgili hicbir bilgi tasimiyor).

TX VGA gain ise BILEREK sabit (max, -x 47 -a 1) tutuluyor: daha once
gercek donanimda sadece bu ayarda guvenilir/guclu bir marj (26-31dB)
elde edilmisti; dusuk/degisken gain zayif sinyale yol acti. Gain HER
SINIF ICIN AYNI (47) oldugundan -- yani sinifa gore degil, hepsine esit
uygulandigindan -- bu, "sinif sabit bir gain'e baglanmasin" kuraliyla
CELISMEZ (kural, gain'in siniftan siniftan FARKLILASMASINI/ipucu
tasimasini yasakliyor; hepsine ayni sabit degeri uygulamak guvenlidir).

Kullanim (CMD):
  python gen_signal.py --mod FM --out C:\\DAT\\scripts\\tx_out.iq

Cikti (stdout, panel.py bunu parse eder):
  FREQ_HZ=435231000
  TX_GAIN=47
  FILE=C:\\DAT\\scripts\\tx_out.iq
"""

import argparse
import numpy as np
from scipy.signal import upfirdn

FS = 2e6
DURATION_SEC = 2.0          # dosya suresi (repeat/-R ile TX surekli dongu yapar)
N_SAMPLES = int(FS * DURATION_SEC)

# Dosyadaki (dijital) genligi HER TIP ICIN AYNI hedefe (tepe ~PEAK_TARGET)
# normalize ediyoruz. Bu, int8 dinamik araligini (+-127) her modulasyon
# icin ayni sekilde ve olabildigince verimli kullanir (kirpma yok, gereksiz
# zayiflatma yok). Gercek RF gucu zaten -x/-a (asagida sabit=max) tarafindan
# belirleniyor; dosyadaki bu normalizasyon sadece sayisal/quantizasyon
# gurultusunu asgaride tutmak icindir ve TUM siniflara ESIT uygulanir.
PEAK_TARGET = 115.0

RX_CENTER_FREQ = 435.0e6   # feature_extractor_v1.py / signal_channelizer_v1.py ile AYNI olmali
TX_FREQ = RX_CENTER_FREQ   # sabit -- artik rastgele degil (yukaridaki notu oku)
TX_GAIN = 47               # sabit, MAX -- daha once dogrulanan guvenilir ayar
TX_AMP_ENABLE = 1          # sabit, ON  -- ayni sekilde dogrulanan ayar

# Dosya icindeki artik tasiyici ofseti: TUM tipler icin AYNI dagilim.
# ~300kHz civari daha once gercek donanimda dogrulanmis guvenli bolge.
CFO_MIN = 250e3
CFO_MAX = 350e3


def random_cfo(rng):
    return rng.uniform(CFO_MIN, CFO_MAX)


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
    f_mod = rng.uniform(300, 3000)
    depth = rng.uniform(0.4, 0.9)
    cfo = random_cfo(rng)
    t = np.arange(n_samples) / fs
    msg = np.cos(2 * np.pi * f_mod * t)
    envelope = 1.0 + depth * msg
    carrier = np.exp(1j * 2 * np.pi * cfo * t)
    return envelope * carrier


def gen_fm(n_samples, fs, rng):
    f_mod = rng.uniform(300, 3000)
    dev = rng.uniform(20e3, 80e3)
    cfo = random_cfo(rng)
    t = np.arange(n_samples) / fs
    phase = 2 * np.pi * cfo * t + (dev / f_mod) * np.sin(2 * np.pi * f_mod * t)
    return np.exp(1j * phase)


def gen_psk(n_samples, fs, rng, order=2):
    # symbol_rate/excess_bw araligi, kanalizasyon filtresinin (CHANNEL_BW=400kHz,
    # yani +-200kHz) yarim-genislik payini asmayacak sekilde sinirlandirildi
    # (en genis durumda 280e3*(1+0.4)/2 = 196kHz < 200kHz).
    symbol_rate = rng.uniform(200e3, 280e3)
    sps = max(int(fs / symbol_rate), 2)
    excess_bw = rng.uniform(0.3, 0.4)
    cfo = random_cfo(rng)
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
    carrier = np.exp(1j * 2 * np.pi * cfo * n / fs)
    return (baseband * carrier)[:n_samples]


GENERATORS = {
    "AM": lambda rng: gen_am(N_SAMPLES, FS, rng),
    "FM": lambda rng: gen_fm(N_SAMPLES, FS, rng),
    "BPSK": lambda rng: gen_psk(N_SAMPLES, FS, rng, order=2),
    "QPSK": lambda rng: gen_psk(N_SAMPLES, FS, rng, order=4),
}


def write_iq_int8(sig, filename):
    # Tum tipler icin AYNI hedefe (PEAK_TARGET) peak-normalize ediyoruz --
    # sinifa gore FARKLILASAN bir olcek yok, dolayisiyla bu adim herhangi
    # bir class-specific ipucu eklemiyor.
    peak = np.max(np.abs(sig)) + 1e-12
    scaled = (sig / peak) * PEAK_TARGET
    iq = np.empty(2 * len(scaled), dtype=np.int8)
    iq[0::2] = np.clip(scaled.real, -127, 127).astype(np.int8)
    iq[1::2] = np.clip(scaled.imag, -127, 127).astype(np.int8)
    iq.tofile(filename)


def generate(mod, out_path, seed=None):
    mod = mod.upper().strip()
    if mod not in GENERATORS:
        raise ValueError(f"Bilinmeyen modulasyon: {mod}. Gecerli: {list(GENERATORS.keys())}")

    rng = np.random.default_rng(seed)
    sig = GENERATORS[mod](rng)
    write_iq_int8(sig, out_path)

    # TX frekansi ve gain artik SABIT (yukaridaki notu oku); rastgelelik
    # sadece dosya icindeki cfo'da (her GENERATORS[mod] cagrisi icinde).
    tx_freq = TX_FREQ
    tx_gain = TX_GAIN

    return tx_freq, tx_gain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, help="AM / FM / BPSK / QPSK")
    ap.add_argument("--out", required=True, help="cikti .iq dosya yolu")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    tx_freq, tx_gain = generate(args.mod, args.out, seed=args.seed)

    print(f"FREQ_HZ={int(tx_freq)}")
    print(f"TX_GAIN={tx_gain}")
    print(f"FILE={args.out}")


if __name__ == "__main__":
    main()
