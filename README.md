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
       ◄──────────── sonuçlar ─────────── AXI DMA / ZedBoard PL
                                                  │
                                     Hann → 4096 FFT → Güç
                                                  │
                                     Uyarlanabilir tespit → Adaylar
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
| Uyarlanabilir hücre tespiti, aday gruplama ve 2/3 zamansal doğrulama | Host referansında doğrulandı |
| Emisyon merkezi, gözlenen taşıyıcı, OBW99, göreli güç, SNR ve sınırlı sinyal türü ölçümü | Operatör onaylı analiz aralığında doğrulandı |
| Manuel açı–güç ölçümüne dayalı bağıl geliş açısı ve kerteriz | Host modelinde doğrulandı; saha doğruluğu ölçülmedi |
| ZedBoard PL Hann/FFT/güç zinciri | Vivado sentez/yerleştirme-yönlendirme kanıtı mevcut |
| ZedBoard üzerinde canlı DMA ve uçtan uca çalışma | Henüz doğrulanmadı |
| AM/NFM izleme zinciri | Kayıtlı I/Q üzerinde doğrulandı; ürün arayüzüne henüz alınmadı |
| ET işlevleri | Yalnız çevrimdışı modeller; RF yayın yolu yok |

Parametre sonuçları kalibrasyonsuz `dBFS` ölçeğindedir; `dBm` ölçümü değildir.
Faz uyumlu çok kanallı DoA, menzil veya otomatik hedef konumu üretilmez.

## Operatör uygulaması

Uygulama; veri kaynağı, spektrum/spektrogram, tespitler, üç adımlı sinyal ölçümü,
manuel yön bulma, sistem sağlığı ve salt okunur olay konsolunu tek görev kabuğunda
birleştirir. Yayın çalışma zamanı yalnız SigMF ve gerçek HackRF RX kaynaklarını
kabul eder; test verileri ve çevrimdışı laboratuvar araçları ürün paketine girmez.

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
- `Boşluk`: taramayı başlatır veya duraklatır.
- `Ctrl+1`, `Ctrl+2`, `Ctrl+3`: çalışma alanları arasında geçer.
- `Ctrl+B`: veri kaynağı panelini açar veya kapatır.

## Doğrulama

Tam yazılım regresyonu:

```powershell
python -B -m unittest discover -s tests
```

Operatör arayüzü; 1280×720, 1366×768, 1920×1080 ve %150 ölçek koşullarında
aşağıdaki doğrulayıcıyla yeniden üretilebilir:

```powershell
python -B scripts\verify_app_f_release_ui.py
```

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
