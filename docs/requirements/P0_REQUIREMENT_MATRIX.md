# P0 Zorunlu EH Çekirdeği Gereksinim Matrisi

Bu matris 2026 zorunlu görevlerini KTR algoritma niyeti, gerçek donanım ve
repository kanıtlarıyla eşler. `Tam` yalnız mevcut tekrarlanabilir kanıtı,
`Kısmi` ise eksik kabul katmanı bulunan çalışmayı belirtir. ADR-0037'nin
257-bin üzeri iki taraflı geniş bant ve ADR-0040 zayıf dar bant yolu
referans/RTL/paket simülasyonunda geçmiş; güncel sentez/bitstream ve sayısal kart
kabulü tamamlanmıştır. Kontrollü kör RF kabulü açık kalmıştır.

| Zorunlu öğe | KTR algoritma niyeti | Gerçek donanım / sahip | Gate A başlangıcı | P0 sonucu |
|---|---|---|---|---|
| Sinyal tespiti | Pencereli FFT/PSD, yerel gürültü, OS-CFAR ve geniş bant enerjisi | Kaba arama: host Python/NumPy 8 MHz; ayrıntılı doğrulama PL: SystemVerilog Hann/FFT/güç/tespit/gruplama/paket; PS: C paket doğrulama ve temporal | Kısmi | 29 Ağustos aday-paket fiziksel kabulünde 54 aday alanı ve 2/3 yaşam döngüsü referansla eşleşti. Beş kayıtlı-I/Q koşusunda 20.480 kare ve en düşük 508,759 kare/s ile 2 MS/s hizmet kapısı geçti. ADR-0037 iki taraflı geniş bant referansı yazılım/RTL simülasyonunda geçti. ADR-0038 8 MHz host kaba adayında 100 kHz–4 MHz sentetik aileleri 32/32 ve üç gürültü negatifini 0/32 geçirdi; sarı host adayı FPGA doğrulamasından ayrıdır. 6 MHz garanti edilmez, 8 MHz tam doluluk açıktır. Pencere kenarı için 600 kHz sorumluluk adımlı örtüşen ayarlar ve geniş adayda mutlak destek örtüşmeli ikinci ayar host testinde geçti. Güncel ADR-0040 kart/bitstream ve dijital işlev-hız kabulü geçmiştir; kontrollü RF Pd/Pfa, kalibrasyon ve bilinmeyen yayın kabulü açıktır. Ayrıntı: `docs/interfaces/SIGNAL_DETECTION_STATUS.md` |
| Emisyon merkez frekansı | Aday bölgesinde güç ağırlıklı spektral merkez; ayrı taşıyıcı frekansı kestirimi yok | PS/ARM; host referansı | Eksik | P0 host referansı — sabit golden hata/tolerans geçti; PHASE-04 bağımsız doğrulaması açık |
| Bant genişliği | Yerel gürültü/eşik referanslı alt ve üst sinyal sınırı | PS/ARM; host oracle | Eksik | Host estimator PASS — 6 dB threshold kenarı, açık %98 fallback ve kaba aday ayrımı; ARM/canlı RF yok |
| Güç seviyesi | Göreli lineer güç ve dBFS; kalibrasyon sözleşmesi | PS/ARM | Eksik | Tam göreli ölçüm — dBFS doğrulandı; sonuç `KALİBRE EDİLMEMİŞ · dBFS`, dBm yok |
| SNR | Aday sinyal gücü / aynı yerel gürültü kestirimi | PS/ARM | Eksik | Tam host algoritması — aynı OS-CFAR gürültü tanımı kullanıldı |
| Analog/Sayısal | Spektral flatness, zarf, anlık frekans sürekliliği ve zaman-frekans davranışı | PS/ARM | Eksik | Tam P0 deterministic açıklanabilir sınıflandırıcı — modülasyon tanıma yok |
| Analog telsiz dinleme | Seçili olay; DDC, kanal filtresi, AM/NFM, 48 kHz mono PCM16/WAV | Bilgisayar-1; HOST/REPLAY, ileride HackRF-1 | Kısmi | AM/NFM bilinen ses fixture'larında bağımsız ton/korelasyon oracle'ı ve UI binding PASS; canlı HackRF/audio saha kabulü yok |
| Genlik tabanlı yön bulma | Açı başına göreli güç; ham maksimum LOB ve güven | Bilgisayar-1, HackRF-1, yönlü anten; manuel dönüş | Eksik | Host model/UI — 7 köşe fixture'ı + bağımsız üç gizli-yön eğitim sahnesi, 0/360 hata ve açık `KUZEY / 0°`/`MANUEL COĞRAFİ BAŞ` referansıyla coğrafi LOB sunumu PASS; PC konumu yalnız işletim sistemi fix döndürürse kullanılır; canlı saha ölçümü yok |
| Sürekli karıştırma | Tekli, çoklu, baraj ve süpürmeli taban bant dalga şekilleri | Bilgisayar-2; iletimsiz/loopback; Faraday `CABLED_LAB` politika onaylı | Kısmi | ET-A offline matematik kapısı geçti; iki kuyruklu OBW99 ve spektrum doğrulandı. ADR-0043 ile laboratuvar ortamı onaylandı; gerçek zaman/HackRF TX ve fiziksel ölçüm yok |
| Arabakışlı karıştırma | Alım/görev zaman paylaşımı, gecikme, koruma ve görev çevrimi | Bilgisayar-2; iletimsiz; Faraday `CABLED_LAB` politika onaylı | Kısmi | ET-B offline zamanlama kapısı geçti; dinleme ve görev pencereleri ayrık, maske ve `%12,5` varsayılan görev çevrimi doğrulandı. Gerçek zamanlı deadline, HackRF-2 ve RF TX yok |
| Analog telsiz aldatma | Test sesi normalizasyonu/bant sınırlama, AM/FM/NFM kompleks taban bant | Bilgisayar-2; iletimsiz/loopback; Faraday `CABLED_LAB` politika onaylı | Kısmi | ET-A AM/FM/NFM yerel loopback geçti; gerçek ses kaynağı, HackRF TX ve fiziksel ölçüm yok |
| ED operatör uygulaması | Görev, spektrum/waterfall, tespit, parametre, üç hakem arama modu, DF, gerçek basemap üzerinde yön gösterimi ve sistem durumu | Bilgisayar-1 PySide6 | Kısmi | Replay seçim kimliği/FFT/P0 parametre worker bağı, MapLibre gerçek harita sağlayıcı zinciri, tek seferlik PC konum isteği/manuel fallback, kaynak-doğruluk ayrımı ve geodezik tek LOB sunumu tamamlandı. Canlı ürün oturumu gerçek HackRF → kanal seçici → ZedBoard FPGA/ARM yoluna bağlandı; spektrum aynı gerçek I/Q'dan, tespitler yalnız kart ABI v3 yanıtından gelir. Kart kapalı fail-closed UI ve fiziksel durdurma/yeniden başlatma geçti. Ayrı görsel FFT işçisiyle güncel RX-only arayüz 15 dakika / 439.454 kareyi sıfır USB taşması, 30,51 taze görüntü/s ve 21,82 ms p95 veri yaşıyla tamamladı; bu kayıt FPGA kabulü değildir. Canlı GNSS, hedef konumu, canlı parametre/ses ve kontrollü RF doğruluğu açıktır |
| PC↔ZedBoard taşıma | Sınırlı sıralı IQ çerçeveleri, bütünlük ve istatistik | Bilgisayar-1 Ethernet; ZedBoard PS | Tam | 8→2 MS/s stateful kanal seçici, 193 tap anti-alias FIR, tam CI8/4096 çerçeve, sürüm 2 çift CRC ve sürekli dört derinlikli ağ köprüsü geçti. Kalıcı imajın soğuk açılışı sonrası kayıtlı-I/Q kapısı 20.480/20.480 kare ve 505,18 kare/s en düşük hızla; tek süreçli canlı HackRF kapısı 20.480/20.480 kare, sıfır USB overrun/sıra hatası ve 488,75 kare/s en düşük hızla geçti |
| HackRF-1 RX | Replay ile aynı normalize IQ frame sözleşmesi | HackRF-1 USB→Bilgisayar-1 | Kısmi | Yapılandırılmış seriyle fiziksel bounded 8 MS/s RX ve host tespiti 5/5 geçti. Kesintisiz stdout RX beş koşuda toplam 681.574.400 baytı sıfır USB overrun ve doyumla kanal seçici üzerinden FPGA'ya taşıdı. Ürün arayüzü bağı, olay decoderı ve bağlantısız durum testleri geçti. Sınırlı ham RX kuyruğuyla ayrıştırılmış ürün sekiz tam oturumda 32.768 kareyi sıfır USB/CRC/sıra hatası/kırpılmayla işledi; fiziksel iptal ve yeniden başlatma da geçti. Güncel 8 MS/s RX-only arayüz kabulünde 439.454/439.454 kare sıfır USB taşmasıyla geçti; ham/kanal kuyruk tepeleri 28/512 ve 7/64, taze görüntü hızı 30,51/s ve p95 veri yaşı 21,82 ms oldu. Önceki FPGA taşıma kabulleri kendi kaynak sürümüne bağlıdır. Kontrollü RF doğruluğu kabulü açıktır |
| Kanonik PL runtime | AXI4-Stream IQ→Hann→4096 FFT→güç→OS-CFAR/geniş bant ve zayıf adaylar→paket | ZedBoard PL + PS/ARM | Kısmi | Güncel ADR-0040 RTL, 50 MHz sentez/route/timing/bitstream/XSA, PetaLinux P09 ve soğuk açılış sayısal kart kabulü geçti. 104-adaylı işlev dizisi aday kaybetmedi; beş koşu/20.480 kare minimum 525,83 kare/s ve sıfır sıra hatasıyla geçti. Geniş fiziksel yayın ailesi, kör Pd/Pfa ve kalibre RF doğruluğu henüz kabul edilmedi. Kanıt: `adr0040-physical-acceptance.json`. |
| Vivado DMA mimarisi | PS DDR↔AXI DMA↔P0 DSP, saat/reset/interrupt | ZedBoard | Kısmi | 8.192-byte CI8 giriş ve 64–54.144-byte aday paketi çıkışı; 16-bit actual-length sürücüsü kalıcı PetaLinux imajında ve fiziksel kartta doğrulandı. Dört derinlikli hizmet istek sırası ölçüldü; bunu PL ping-pong tamponu olarak yorumlamayın. Fiziksel Ethernet kabulü kendi kaynak sürümüne bağlıdır. |

## KTR Donanım Sapma Kaydı

| KTR işlevi | KTR eski donanımı | Güncel donanım | Algoritma korundu mu? | Uygulama değişikliği | Yarışma etkisi |
|---|---|---|---|---|---|
| ED alma | bladeRF tabanlı alıcı | HackRF-1 + Bilgisayar-1 | Evet | USB host bilgisayardır; IQ Ethernet ile ZedBoard PS'ye gider | P0 işlevi korunur; anlık bant HackRF sınırındadır |
| FPGA işleme | Eski SDR/işlemci zinciri | ZedBoard Zynq-7000 | Evet | Hann/FFT/güç PL, karar çekirdeği PS olur | PetaLinux gelene kadar host oracle; kart çalışması ayrıca kabul edilir |
| Yön bulma | KrakenSDR/faz uyumlu çok kanal ve motor | HackRF-1 + tek yönlü anten + manuel açı | Kısmen | MUSIC/faz/TDOA yerine KTR genlik maksimumu | Zorunlu DF sağlanır; otomatik/faz hassasiyeti iddia edilmez |
| Konum | Çoklu LOB/ek donanım | P0 envanterinde zorunlu değil | Hayır, P1'e ertelendi | P0'da yalnız sensör ve tek LOB yön gösterimi vardır; hedef konumu/çoklu LOB yok | Zorunlu P0 çekirdeğini etkilemez |
| Sürekli ET | bladeRF veya eski TX zinciri | HackRF-2 + Bilgisayar-2 | Evet | Önce iletimsiz/loopback taban bant; Faraday `CABLED_LAB` politika onaylı, genel TX kilitli | Dalga şekli kanıtlanır; RF etki/güç iddiası yok |
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
