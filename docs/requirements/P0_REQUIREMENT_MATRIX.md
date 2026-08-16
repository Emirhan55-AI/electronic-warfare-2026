# P0 Zorunlu EH Çekirdeği Gereksinim Matrisi

Bu matris 2026 zorunlu görevlerini KTR algoritma niyeti, gerçek donanım ve
repository kanıtlarıyla eşler. `Tam` yalnız mevcut tekrarlanabilir kanıtı,
`Kısmi` ise eksik kabul katmanı bulunan çalışmayı belirtir.

| Zorunlu öğe | KTR algoritma niyeti | Gerçek donanım / sahip | Gate A başlangıcı | P0 sonucu |
|---|---|---|---|---|
| Sinyal tespiti | Pencereli FFT/PSD, yerel gürültü, guard/reference, OS-CFAR, aday gruplama | ZedBoard PL Hann/FFT/güç; PS OS-CFAR/aday/temporal | Kısmi | Host profile PASS — Pfa `1e-4` türetilmiş alpha, empirical FAR ve Python/C eşdeğerliği; ARM çalıştırılmadı |
| Taşıyıcı frekansı | Aday bölgesinde güç ağırlıklı spektral centroid | PS/ARM; host oracle | Eksik | Tam host algoritması — golden hata/tolerans geçti |
| Bant genişliği | Yerel gürültü/eşik referanslı alt ve üst sinyal sınırı | PS/ARM; host oracle | Eksik | Host estimator PASS — 6 dB threshold kenarı, açık %98 fallback ve kaba aday ayrımı; ARM/canlı RF yok |
| Güç seviyesi | Göreli lineer güç ve dBFS; kalibrasyon sözleşmesi | PS/ARM | Eksik | Tam göreli ölçüm — dBFS doğrulandı; dBm `KALİBRASYON BEKLİYOR` |
| SNR | Aday sinyal gücü / aynı yerel gürültü kestirimi | PS/ARM | Eksik | Tam host algoritması — aynı OS-CFAR gürültü tanımı kullanıldı |
| Analog/Sayısal | Spektral flatness, zarf, anlık frekans sürekliliği ve zaman-frekans davranışı | PS/ARM | Eksik | Tam P0 deterministic açıklanabilir sınıflandırıcı — modülasyon tanıma yok |
| Genlik tabanlı yön bulma | Açı başına göreli güç; ham maksimum LOB ve güven | Bilgisayar-1, HackRF-1, yönlü anten; manuel dönüş | Eksik | Tam host model/UI — 7 fixture geçti; canlı saha ölçümü yok |
| Sürekli karıştırma | Tekli, çoklu ve barrage taban bant dalga şekilleri | Bilgisayar-2; P0'da iletimsiz/loopback | Eksik | Tam P0 taban bant/UI — spektrum doğrulandı; TX kilitli |
| Analog telsiz aldatma | Ses normalizasyonu/bant sınırlama, FM/NFM kompleks taban bant | Bilgisayar-2; P0'da iletimsiz/loopback | Kısmi | Tam P0 taban bant/UI — FM/NFM loopback geçti; TX kilitli |
| ED operatör uygulaması | Görev, spektrum/waterfall, tespit, parametre, üç hakem arama modu, DF ve sistem durumu | Bilgisayar-1 PySide6 | Kısmi | Replay/host `UNKNOWN`/`JUDGE_BAND`/`JUDGE_FREQUENCY` ve yeni bant binding PASS; canlı HackRF yok |
| PC↔ZedBoard taşıma | Bounded sıralı IQ çerçeveleri, bütünlük ve istatistik | Bilgisayar-1 Ethernet; ZedBoard PS | Eksik | PC sözleşmesi/loopback tam; ZedBoard sunucusu ve canlı ağ çalıştırılmadı |
| HackRF-1 RX | Replay ile aynı normalize IQ frame sözleşmesi | HackRF-1 USB→Bilgisayar-1 | Kısmi | Soyutlama/mock tam; `BLOCKED_TOOLCHAIN`, canlı HackRF yok |
| Kanonik PL runtime | AXI4-Stream IQ→Hann→4096 FFT→lineer güç | ZedBoard PL | Eksik | Vivado sentez/route/timing/bitstream geçti; kartta çalıştırılmadı |
| Vivado DMA mimarisi | PS DDR↔AXI DMA↔P0 DSP, saat/reset/interrupt | ZedBoard | Eksik | BD validate geçti; gerçek bloklar bağlı; PetaLinux/driver/DMA çalıştırılmadı |

## KTR Donanım Sapma Kaydı

| KTR işlevi | KTR eski donanımı | Güncel donanım | Algoritma korundu mu? | Uygulama değişikliği | Yarışma etkisi |
|---|---|---|---|---|---|
| ED alma | bladeRF tabanlı alıcı | HackRF-1 + Bilgisayar-1 | Evet | USB host bilgisayardır; IQ Ethernet ile ZedBoard PS'ye gider | P0 işlevi korunur; anlık bant HackRF sınırındadır |
| FPGA işleme | Eski SDR/işlemci zinciri | ZedBoard Zynq-7000 | Evet | Hann/FFT/güç PL, karar çekirdeği PS olur | PetaLinux gelene kadar host oracle; kart çalışması ayrıca kabul edilir |
| Yön bulma | KrakenSDR/faz uyumlu çok kanal ve motor | HackRF-1 + tek yönlü anten + manuel açı | Kısmen | MUSIC/faz/TDOA yerine KTR genlik maksimumu | Zorunlu DF sağlanır; otomatik/faz hassasiyeti iddia edilmez |
| Konum | Çoklu LOB/ek donanım | P0 envanterinde zorunlu değil | Hayır, P1'e ertelendi | P0'da harita/konum yok | Zorunlu P0 çekirdeğini etkilemez |
| Sürekli ET | bladeRF veya eski TX zinciri | HackRF-2 + Bilgisayar-2 | Evet | Önce iletimsiz/loopback taban bant; TX kilitli | Dalga şekli kanıtlanır; RF etki/güç iddiası yok |
| Analog aldatma | Eski TX platformu | HackRF-2 + Bilgisayar-2 | Evet | FM/NFM taban bant ve bounded görev nesnesi | Zorunlu algoritma gösterilir; açık alan TX yok |
| Kontrol bilgisayarı | Raspberry Pi/dağıtık Python varsayımları | İki bağımsız bilgisayar | İşlevsel niyet evet | ED ve ET süreçleri Python durumu paylaşmaz | Operasyonel ayrım güçlenir |
| Anten yönlendirme | Motorlu konumlayıcı | FOX-727 veya uygun banttaki UWB yönlü anten | Genlik algoritması evet | Açı operatörce girilir | Daha yavaş ama P0 için tekrarlanabilir manuel akış |

## Gerçek Donanım Kaynağı

- 2 × HackRF One + PortaPack H2
- 1 × ZedBoard, Zynq-7000, P/N 410-248
- 1 × FOX-727 çift bant Yagi
- 2 × Quectel YE0003AA geniş bant omni anten
- 1 × Diamond SRH-789 teleskopik anten
- 1 × 800 MHz–6 GHz UWB yönlü anten
- 1 × 2,4–10,5 GHz UWB yönlü TEM anten; HackRF çalışma bandı ile sınırlı
- Mevcut RF kabloları, adaptörler ve zayıflatıcı
- 2 × bilgisayar

Listede bulunmayan bladeRF, KrakenSDR, Raspberry Pi, motor, faz uyumlu çok
kanallı alıcı veya ek GNSS donanımı P0 bağımlılığı değildir.
