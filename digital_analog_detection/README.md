# Digital / Analog RF Modulation Detection

Gercek zamanli, iki HackRF One (TX + RX) kullanan bir RF sinyal siniflandirma
sistemi. Amac: havadan alinan bir sinyalin **ANALOG** (AM/FM) mi yoksa
**DIGITAL** (BPSK/QPSK) mi oldugunu, gercek modulasyon etiketini hicbir
sekilde gormeden, sadece sinyalin fiziksel/istatistiksel ozelliklerinden
karar vermek.

## Pipeline

```
SIGNAL/NO-SIGNAL tespiti
        |
Tasiyici (CFO) kestirimi
        |
Kanal filtreleme (channelize)
        |
Bant genisligi kestirimi
        |
Normalizasyon (DC + guc)
        |
Modulasyondan bagimsiz ozellik cikarma
        |
ANALOG / DIGITAL siniflandirma (Logistic Regression)
```

## Tasarim ilkeleri (kritik)

- **Label leakage yok**: RX/algilama tarafi, iletilen gercek modulasyon
  etiketini hicbir zaman gormez. `panel.py` icindeki `RXWorker` thread'i,
  panelde kullanicinin ne yazdigindan tamamen habersiz calisir; sadece
  havadan gelen ham IQ akisindan karar uretir.
- **Shortcut learning'e karsi rastgelelik**: Hicbir modulasyon sinifi sabit
  bir frekans/kazanc/mesafeye baglanmaz. Her TX uretiminde tasiyici ofseti,
  modulasyon parametreleri (derinlik/sapma/sembol hizi/excess bandwidth) ve
  SNR rastgele secilir -- boylece siniflandirici gercekten sinyalin
  fiziksel karakterinden (zarf/frekans varyasyonu, kumulantlar) ogrenir,
  yan bilgilerden degil.

## Dosyalar

| Dosya | Aciklama |
|---|---|
| `signal_channelizer_v1.py` | Genis bant SIGNAL/NO-SIGNAL tespiti, CFO kestirimi, kanalizasyon, bant genisligi olcumu. Gercek donanimda dogrulanmis (RRC-BPSK ile margin ~26-31dB, CFO hatasi ~1-3kHz). |
| `feature_extractor_v1.py` | ZMQ'dan ham IQ okur, `signal_channelizer_v1.py` mantigini kullanarak sinyali kanallar, normalize eder ve 6 modulasyondan-bagimsiz ozellik cikarir: `std_amp`, `kurt_amp`, `std_freq`, `kurt_freq`, `gamma_max`, `abs_C42`. |
| `train_classifier.py` | Sentetik AM/FM/BPSK/QPSK verisiyle (rastgele SNR, rastgele modulasyon parametreleri) `feature_extractor_v1.py` ile BIREBIR AYNI ozellik cikarma mantigini kullanarak bir Logistic Regression siniflandirici egitir. Test dogrulugu: **%97.4** (AM %98.4, FM %91.1, BPSK %100, QPSK %100). |
| `classifier_model.py` | `train_classifier.py` tarafindan uretilen egitilmis agirliklar. Sadece NumPy ile calisir (sklearn gerekmez) -- `panel.py` icinde canli siniflandirma icin kullanilir. |
| `gen_signal.py` | Panelin TX tarafi. "AM"/"FM"/"BPSK"/"QPSK" icin gercek donanima (`hackrf_transfer`) verilecek int8 IQ dosyasi uretir. TX frekansi RX ile sabit ayni (435.0MHz); rastgelelik sadece dosya icindeki tasiyici ofsetinde (250-350kHz). TX kazanci sabit maksimumda (47, amp on) -- daha once gercek donanimda dogrulanan guvenilir ayar. |
| `panel.py` | Tkinter GUI. Modulasyon adi yazip "Gonder" ile TX baslatilir (kisa ~2sn'lik gecisler halinde surekli tekrarlanir, her gecis kendi dogal sonunda kendiliginden kapanir -- sinyal/interrupt'a gerek yok). RX tarafi ayri bir thread'de canli istatistikleri ve ANALOG/DIGITAL kararini gosterir. |
| `hackrf_inspector.grc` | RX flowgraph (GNU Radio Companion). HackRF'ten ornek okuyup ZMQ PUB (`tcp://127.0.0.1:5555`) uzerinden yayinlar. `panel.py` ve `feature_extractor_v1.py` bu akisi dinler. |

## Donanim

- 2x HackRF One (klon), biri TX biri RX olarak kullanilir.
- TX seri no: `a32868dc35138247`
- RX seri no: `a32868dc36877e47`
- RX merkez frekans: 435.0 MHz, ornekleme hizi: 2 Msps.

## Kurulum ve calistirma (Windows, radioconda ortami)

```
pip install pyzmq numpy scipy scikit-learn
```

1. GNU Radio Companion'da `hackrf_inspector.grc`'yi ac ve calistir (RX
   flowgraph ayakta kalmali).
2. Ayri bir CMD penceresinde:
   ```
   cd /d C:\DAT\scripts\digital_analog_detection
   python panel.py
   ```
3. Panelde modulasyon yaz (AM/FM/BPSK/QPSK), "Gonder (Start TX)" bas.
   Alttaki "RX Canli Istatistikler" ve "KARAR" alani canli guncellenir.

## Siniflandiriciyi yeniden egitmek

```
cd /d C:\DAT\scripts\digital_analog_detection
python train_classifier.py
```

Ciktida yazdirilan `SCALER_MEAN` / `SCALER_SCALE` / `CLF_COEF` /
`CLF_INTERCEPT` degerlerini `classifier_model.py` icine kopyalamak yeterli
(dosyanin geri kalani degismez).
