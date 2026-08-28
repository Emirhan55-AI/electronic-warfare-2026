# Elektronik Harp Operatör ve FPGA Sinyal İşleme Sistemi

Bu proje; RF I/Q verisinin alınması, spektral analizi, sinyal tespiti, operatör
onaylı parametre ölçümü ve FPGA üzerinde gerçek zamanlı işlenmesi için geliştirilen
bir mühendislik sistemidir. Referans platform HackRF One, ZedBoard Zynq-7000 ve
Türkçe Qt Quick operatör uygulamasından oluşur.

Proje yalnız ölçülmüş veya tekrarlanabilir testle doğrulanmış sonuçları yetenek
olarak kabul eder. Canlı donanım, RF doğruluğu ya da performans kanıtı bulunmayan
işlevler uygulamada çalışıyormuş gibi gösterilmez.

## Sistem mimarisi

```text
SigMF / HackRF RX
       │
       ▼
Operatör bilgisayarı ── kontrol ve kayıt ──► ZedBoard PS / DDR
       │                                         │
       │                                         ▼
       ◄──────────── sonuçlar ───── ZedBoard PS: OS-CFAR + geniş bant kurtarma
                                                  │
                                                  └──────────► 2/3 → Parametre
                                                  ▲
                                               AXI DMA
                                                  ▲
                                     ZedBoard PL: Hann → 4096 FFT → Güç
```

Hedef mimaride kritik FPGA sonuçları sürümlü ve sınırları belirli paketlerle PS
tarafına taşınır. Host referans modelleri RTL davranışını doğrulamak için korunur;
nihai gerçek zamanlı işleme sahibi FPGA/PS zinciridir.

## Mevcut yetenekler

| Alan | Durum |
|---|---|
| SigMF kayıt açma, sözleşme denetimi ve gerçek I/Q işleme | Doğrulandı |
| HackRF araç/cihaz denetimi ve sınırlandırılmış RX alımı | Yazılım yolu hazır; fiziksel kabul bekliyor |
| Hann, 4096 FFT, dBFS spektrum ve spektrogram | Host referansında doğrulandı |
| Uyarlanabilir hücre tespiti, bütünleşik geniş bant enerjisi, aday gruplama ve 2/3 zamansal doğrulama | Host referansı ve fiziksel PL→DMA→ARM zincirinde doğrulandı; canlı RF ve sürekli throughput bekliyor |
| Emisyon merkezi, gözlenen taşıyıcı, OBW99, göreli güç, SNR ve sınırlı sinyal türü ölçümü | Host ürün profilinde operatör onaylı analiz aralığında doğrulandı; emisyon merkezi, bant kenarları, OBW99, kalibrasyonsuz dBFS güç ve SNR fiziksel PL→DMA→ARM zincirinde dört gözlemle çalıştı. Taşıyıcı çizgisi ve sinyal türü ARM paketinde yok |
| Manuel açı–güç ölçümüne dayalı bağıl geliş açısı ve kerteriz | Host modelinde doğrulandı; saha doğruluğu ölçülmedi |
| ZedBoard PL Hann/FFT/güç zinciri | SystemVerilog ve AMD FFT IP ile temiz Vivado bitstream/XSA üretimi doğrulandı |
| FPGA tespit, gruplama ve aday paketleme blokları | SystemVerilog/golden doğrulaması mevcut; kanonik P0 bitstream zincirine henüz alınmadı |
| ZedBoard üzerinde DMA ve tespit zinciri | Deterministik fiziksel karelerde PL güç → ARM OS-CFAR + 32-bin bütünleşik enerji → 2/3 doğrulandı; geniş bant dizisinde tek olay sahibi ve gürültü-negatif kapı geçti. Sürekli throughput ve canlı RF ölçülmedi |
| AM/NFM izleme zinciri | Kayıtlı I/Q ve QML ürün akışında doğrulandı; canlı HackRF/ses saha kabulü bekliyor |
| ET işlevleri | Python host üzerinde çevrimdışı/loopback modeller; SystemVerilog, FPGA veya RF yayın yolu yok |

Parametre sonuçları kalibrasyonsuz `dBFS` ölçeğindedir; `dBm` ölçümü değildir.
Faz uyumlu çok kanallı DoA, menzil veya otomatik hedef konumu üretilmez.

## Operatör uygulaması

Uygulama ED ve ET görevlerini aynı ürün kabuğunda açıkça ayırır. ED alanı; veri
kaynağı, bağlı spektrum/spektrogram görünümü, tespitler, üç adımlı sinyal ölçümü,
AM/NFM dinleme, manuel yön bulma, sistem sağlığı ve salt okunur olay konsolunu
birleştirir. ET alanı yalnız doğrulanmış çevrimdışı sürekli, arabakışlı, analog
loopback ve GPS L1 C/A metadata modellerini sunar. RF TX yolu yoktur ve bütün ET
sonuçları fiziksel RF sonucu olmadığını açıkça belirtir. Yayın çalışma zamanı
yalnız gerçek SigMF/HackRF RX kaynaklarını ve doğrulanmış çevrimdışı ET
modellerini içerir; mock kaynaklar, gösterim verileri ve eski laboratuvar
arayüzleri ürün paketine girmez.

### Kurulum

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements\phase02.txt
```

### Çalıştırma

```powershell
python -m app.operator_console
```

Klavye kısayolları:

- `Ctrl+O`: SigMF kaydı açar.
- `Boşluk`: Spektrum alanında taramayı başlatır veya duraklatır.
- `Ctrl+1`, `Ctrl+2`, `Ctrl+3`, `Ctrl+4`: çalışma alanları arasında geçer ve
  klavye odağını seçilen alana taşır.
- `Ctrl+5`: ET görev doğrulama alanını açar.
- `Ctrl+B`: Spektrum alanında veri kaynağı panelini açar veya kapatır.
- `Alt+Sol`, `Alt+Sağ`: frekans görünümü geçmişinde geri veya ileri gider.
- `Ctrl+0`: spektrum ve spektrogramı tam banda döndürür.
- `Esc`: açık olay konsolunu kapatır.

## Doğrulama

Tam yazılım regresyonu:

```powershell
python -B -m unittest discover -s tests
```

Operatör arayüzü; ED için 1280×720, 1366×768, 1920×1080 ve %150 ölçek
koşullarında; ET için 1180×680, 1280×720 ve 1440×900 koşullarında aşağıdaki
doğrulayıcıyla yeniden üretilebilir:

```powershell
python -B scripts\verify_app_f_release_ui.py
```

Sistem çalışma alanı etkin işlem zincirini ve host/FPGA kabul sınırını açıkça
ayırır. Filtrelenebilir olay günlüğü çalışma durumunu salt okunur olarak izler;
ürün görünümü komut çalıştıran bir terminal içermez.

Ayrıntılı gereksinim durumu ve yöntem sınırları
[`docs/requirements/KTR_TRACEABILITY.md`](docs/requirements/KTR_TRACEABILITY.md),
sistem hedefi ise
[`docs/architecture/SYSTEM_BASELINE.md`](docs/architecture/SYSTEM_BASELINE.md)
altında tutulur.

## Depo düzeni

- `app/`: Qt Quick operatör uygulaması ve sunum katmanı.
- `algorithms/`: host referans DSP, tespit, parametre, izleme ve FPGA RTL kaynakları.
- `platforms/`: HackRF alım katmanı ile Zynq PS/embedded bileşenleri.
- `profiles/`: doğrulama kapılarını geçmiş çalışma profilleri.
- `tests/` ve `verification/`: otomatik regresyonlar ve bağımsız doğrulama araçları.
- `docs/`: mimari, gereksinim izlenebilirliği ve teknik kararlar.

## RF güvenliği

Depoda genel kullanıma açık bir RF yayın arka ucu bulunmaz. ET çalışmaları yalnız
çevrimdışı veya kapalı çevrim doğrulama kapsamındadır. Her fiziksel RF deneyi;
yetkili, kontrollü, uygun zayıflatma ve ekranlama kullanılan bir test düzeninde
yürütülmelidir.
