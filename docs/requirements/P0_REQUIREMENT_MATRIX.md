# P0 Zorunlu EH Çekirdeği Gereksinim Matrisi

Bu matris 2026 zorunlu görevlerini KTR algoritma niyeti, gerçek donanım ve
repository kanıtlarıyla eşler. `Tam` yalnız mevcut tekrarlanabilir kanıtı,
`Kısmi` ise eksik kabul katmanı bulunan çalışmayı belirtir.

| Zorunlu öğe | KTR algoritma niyeti | Gerçek donanım / sahip | Gate A başlangıcı | P0 sonucu |
|---|---|---|---|---|
| Sinyal tespiti | Pencereli FFT/PSD, yerel gürültü, guard/reference, OS-CFAR, aday gruplama | ZedBoard PL Hann/FFT/güç/seyrek OS-CFAR + geniş bant aday indirgeme + PHASE-06I paketleme; PS paket doğrulama ve temporal | Kısmi | OS-CFAR Pfa `1e-4`, alpha ve empirical FAR geçti. ADR-0030 PL çekirdeği 45.056 DMA kelimesinde bit-doğru, 50 MHz'te 48.910/102.400 çevrim işlevsel kapasiteyle geçti. ADR-0031 paket/typed yolu 33 kare ve 1.501 aday kaydında sıfır fark verdi; ADR-0032 strict/trusted aday yolu hostta sıfır fark verdi. Önceki PetaLinux imajı 5.679/5.679 derlendi. Fiziksel 64+4.096 hizmet koşusu sıfır işlevsel hatayla `196,966411503 kare/s` ölçtü; `488,28125 kare/s` kapısı başarısızdır. ADR-0033 final aday yolu alt blokları bit-doğru geçti. CI8→Hann→AMD 4096 FFT→güç→final candidate reducer→PHASE-06I AXI64 packetizer tam kart tasarımı Vivado 2025.2 ile Zynq-7020 üzerinde 27.453 LUT, 81,5 BRAM tile ve 71 DSP kullanarak route edildi; `WNS=+0,423 ns`, `WHS=+0,021 ns`, setup/hold ihlali, route hatası ve DRC error/critical warning sayıları sıfırdır. Yeni bitstream/XSA hazırdır. Değişken 64–54.144 byte DMA actual-length sözleşmesi host kaynakta uygulanmış ve Linux hizmet kapısında doğrulanmıştır; PetaLinux yeniden derleme, kart ve sürekli hız kabulü ile canlı RF açıktır |
| Emisyon merkez frekansı | Aday bölgesinde güç ağırlıklı spektral merkez; ayrı taşıyıcı frekansı kestirimi yok | PS/ARM; host referansı | Eksik | P0 host referansı — sabit golden hata/tolerans geçti; PHASE-04 bağımsız doğrulaması açık |
| Bant genişliği | Yerel gürültü/eşik referanslı alt ve üst sinyal sınırı | PS/ARM; host oracle | Eksik | Host estimator PASS — 6 dB threshold kenarı, açık %98 fallback ve kaba aday ayrımı; ARM/canlı RF yok |
| Güç seviyesi | Göreli lineer güç ve dBFS; kalibrasyon sözleşmesi | PS/ARM | Eksik | Tam göreli ölçüm — dBFS doğrulandı; sonuç `KALİBRE EDİLMEMİŞ · dBFS`, dBm yok |
| SNR | Aday sinyal gücü / aynı yerel gürültü kestirimi | PS/ARM | Eksik | Tam host algoritması — aynı OS-CFAR gürültü tanımı kullanıldı |
| Analog/Sayısal | Spektral flatness, zarf, anlık frekans sürekliliği ve zaman-frekans davranışı | PS/ARM | Eksik | Tam P0 deterministic açıklanabilir sınıflandırıcı — modülasyon tanıma yok |
| Analog telsiz dinleme | Seçili olay; DDC, kanal filtresi, AM/NFM, 48 kHz mono PCM16/WAV | Bilgisayar-1; HOST/REPLAY, ileride HackRF-1 | Kısmi | AM/NFM bilinen ses fixture'larında bağımsız ton/korelasyon oracle'ı ve UI binding PASS; canlı HackRF/audio saha kabulü yok |
| Genlik tabanlı yön bulma | Açı başına göreli güç; ham maksimum LOB ve güven | Bilgisayar-1, HackRF-1, yönlü anten; manuel dönüş | Eksik | Host model/UI — 7 köşe fixture'ı + bağımsız üç gizli-yön eğitim sahnesi, 0/360 hata ve açık `KUZEY / 0°`/`MANUEL COĞRAFİ BAŞ` referansıyla coğrafi LOB sunumu PASS; PC konumu yalnız işletim sistemi fix döndürürse kullanılır; canlı saha ölçümü yok |
| Sürekli karıştırma | Tekli, çoklu, baraj ve süpürmeli taban bant dalga şekilleri | Bilgisayar-2; P0'da iletimsiz/loopback | Kısmi | ET-A offline matematik kapısı geçti; iki kuyruklu OBW99 ve spektrum doğrulandı; gerçek zaman/RF TX yok |
| Arabakışlı karıştırma | Alım/görev zaman paylaşımı, gecikme, koruma ve görev çevrimi | Bilgisayar-2; P0'da iletimsiz | Kısmi | ET-B offline zamanlama kapısı geçti; dinleme ve görev pencereleri ayrık, maske ve `%12,5` varsayılan görev çevrimi doğrulandı; gerçek zamanlı deadline, HackRF-2 ve RF TX yok |
| Analog telsiz aldatma | Test sesi normalizasyonu/bant sınırlama, AM/FM/NFM kompleks taban bant | Bilgisayar-2; P0'da iletimsiz/loopback | Kısmi | ET-A AM/FM/NFM yerel loopback geçti; gerçek ses kaynağı ve RF TX yok |
| ED operatör uygulaması | Görev, spektrum/waterfall, tespit, parametre, üç hakem arama modu, DF, gerçek basemap üzerinde yön gösterimi ve sistem durumu | Bilgisayar-1 PySide6 | Kısmi | Replay seçim kimliği/FFT/P0 parametre worker bağı, MapLibre gerçek harita sağlayıcı zinciri, tek seferlik PC konum isteği/manuel fallback, kaynak-doğruluk ayrımı ve geodezik tek LOB sunumu; canlı GNSS, hedef konumu ve canlı HackRF saha kabulü yok |
| PC↔ZedBoard taşıma | Sınırlı sıralı IQ çerçeveleri, bütünlük ve istatistik | Bilgisayar-1 Ethernet; ZedBoard PS | Kısmi | 8→2 MS/s stateful kanal seçici; 193 tap anti-alias FIR; tam CI8/4096 çerçeve; sürüm 2 çift CRC; sürekli dört derinlikli PC istemcisi ve Linux TCP→yerel hizmet köprüsü geçti. Kalıcı PetaLinux imajının soğuk açılışı sonrası fiziksel 1 Gbps Ethernet kabulünde beş koşu ve 20.480/20.480 ölçüm karesi sıfır sıra hatası/düşümle tamamlandı; en düşük hız 504,76 kare/s. Kesintisiz canlı HackRF→FPGA bağı açık |
| HackRF-1 RX | Replay ile aynı normalize IQ frame sözleşmesi | HackRF-1 USB→Bilgisayar-1 | Kısmi | Yapılandırılmış seriyle fiziksel bounded 8 MS/s RX ve host tespiti 5/5 geçti; toplam 81.920 kompleks örnek tam, doyum sıfır. Tekrarlı CLI capture kesintisiz USB akışı değildir; ZedBoard/FPGA canlı bağı açık |
| Kanonik PL runtime | AXI4-Stream IQ→Hann→4096 FFT→lineer güç→seyrek OS-CFAR/geniş bant aday indirgeme→PHASE-06I paket | ZedBoard PL | Kısmi | Tam RTL hiyerarşisi kanonik ZedBoard blok tasarımına alındı; sentez, route, 50 MHz setup/hold, DRC, bitstream ve XSA kapıları geçti. Önceki güç-frame bitstream'i fiziksel kartta doğrulanmıştı; yeni aday-paket bitstream'i henüz karta yüklenmedi ve sürekli 2 MS/s gerçek-zaman kapısı açıktır |
| Vivado DMA mimarisi | PS DDR↔AXI DMA↔P0 DSP, saat/reset/interrupt | ZedBoard | Kısmi | Yeni MM2S 8.192-byte CI8 ve S2MM 64–54.144-byte PHASE-06I aday paketi blok tasarımı 16-bit DMA length alanıyla route edildi. Linux sürücüsü 54.144-byte kapasiteyi programlayıp IOC sonrası actual S2MM_LENGTH değerini fail-closed kontrol edecek şekilde güncellendi; PetaLinux yeniden derlemesi, iki-buffer, fiziksel DMA ve Ethernet kabulü beklenmektedir |

## KTR Donanım Sapma Kaydı

| KTR işlevi | KTR eski donanımı | Güncel donanım | Algoritma korundu mu? | Uygulama değişikliği | Yarışma etkisi |
|---|---|---|---|---|---|
| ED alma | bladeRF tabanlı alıcı | HackRF-1 + Bilgisayar-1 | Evet | USB host bilgisayardır; IQ Ethernet ile ZedBoard PS'ye gider | P0 işlevi korunur; anlık bant HackRF sınırındadır |
| FPGA işleme | Eski SDR/işlemci zinciri | ZedBoard Zynq-7000 | Evet | Hann/FFT/güç PL, karar çekirdeği PS olur | PetaLinux gelene kadar host oracle; kart çalışması ayrıca kabul edilir |
| Yön bulma | KrakenSDR/faz uyumlu çok kanal ve motor | HackRF-1 + tek yönlü anten + manuel açı | Kısmen | MUSIC/faz/TDOA yerine KTR genlik maksimumu | Zorunlu DF sağlanır; otomatik/faz hassasiyeti iddia edilmez |
| Konum | Çoklu LOB/ek donanım | P0 envanterinde zorunlu değil | Hayır, P1'e ertelendi | P0'da yalnız sensör ve tek LOB yön gösterimi vardır; hedef konumu/çoklu LOB yok | Zorunlu P0 çekirdeğini etkilemez |
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
