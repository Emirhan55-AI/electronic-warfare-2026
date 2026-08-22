# P0 Offline Doğrulama ve Operatör Kullanımı

## Offline doğrulama uygulaması

Repository kökünde çalıştırın:

```text
python -B scripts/run_p0_demo.py
```

Bu tarihsel script adı yalnız doğrulama uyumluluğu için korunur; kurduğu uygulama
`host.operator_console.laboratory` bileşimidir ve yayın paketi dışındadır.

Gerçek SigMF/HackRF kaynaklarıyla açılan kanonik ürün komutu:

```text
python -B -m host.operator_console
```

Ürün komutu test, eğitim veya offline ET değeri yüklemez. `SigMF Kaydı`
seçiliyken `SigMF Aç` ile metadata
dosyası açılır; doğrulanmış tespit seçimi `PARAMETRELER` ve `Dinleme` sekmeleri
arasında aynı olay kimliğiyle korunur.

İlk sekmede deterministik replay spektrumu, waterfall geçmişi ve doğrulanmış P0
OS-CFAR sonucu görünür. `GÖREV` bölümündeki üç hakem girişi de aynı işleme
zincirini kullanır: IQ → periyodik Hann → FFT → OS-CFAR → 2/3 zamansal onay →
parametre çıkarımı. Arayüz MHz kabul eder; işleme katmanı yalnızca Hz kullanır.

### Doğrulama A — bilinmeyen frekans

1. `Bilinmeyen Frekans` kipini seçin.
2. `Taramayı Başlat` düğmesine basın.
3. Tek bir onaylı sinyal ve aşağıdaki ortak sonuçların görüntülendiğini doğrulayın.

### Doğrulama B — hakem bant bildirdi

1. `Hakem Bant Bildirdi` kipini seçin.
2. Alt sınırı `100.080`, üst sınırı `100.100` MHz girin.
3. `Taramayı Başlat` düğmesine basın ve sinyalin bulunduğunu doğrulayın.

Ters sınırlar, 20 MHz'den geniş bantlar ve 1 MHz–6 GHz alıcı sınırı dışındaki
girişler reddedilir. `99.950`–`99.960` MHz dışlama bandı sinyal üretmez.

### Doğrulama C — hakem frekans bildirdi

1. `Hakem Frekans Bildirdi` kipini seçin.
2. Frekansı `100.090` MHz girin.
3. `Taramayı Başlat` düğmesine basın ve sinyalin bulunduğunu doğrulayın.

Bu kip taşıyıcıyı doğrudan sonuç olarak yazmaz; bildirilen frekans çevresinde
50 kHz pencere toplar ve aynı OS-CFAR/zamansal onay zincirini çalıştırır.
`100.200` MHz yanlış frekans girişi sinyal üretmez.

Üç olumlu senaryonun replay çıktısı, arayüz yuvarlamasıyla şöyledir:

- taşıyıcı: `100.090003 MHz`
- alt/üst sınır: `100.088875` / `100.091125 MHz`
- gerçek bant genişliği: `2.250 kHz`
- kaba aday bant genişliği: `3.250 kHz`
- göreli güç: `-4.44 dBFS` ve `KALİBRASYON BEKLİYOR`
- SNR: `35.63 dB`
- sınıf: `Analog`
- kaynak: `REPLAY`

`PARAMETRELER` sekmesinde taşıyıcı, gürültü/eşik referanslı gerçek bant, göreli
dBFS, SNR, Analog/Sayısal sonucu, backend ve kaynak görünür. Güç alanı
`KALİBRASYON BEKLİYOR` yazar.

`YÖN` sekmesindeki `Ölçüm` görünümünde açı–güç eğrisi ve ham maksimum LOB görünür. Saha akışında
operatör önce `KUZEY / 0° COĞRAFİ`, `MANUEL COĞRAFİ BAŞ` veya `REFERANS YOK`
seçer; sonra fiziksel antenin elle döndürüldüğü `ANTEN AÇISI (MANUEL)` değerini
girer. Uygulama pusula, IMU veya enkoderden anten yönü çıkarmaz. `GÜÇ ÖLÇ` ancak
seçili ve işlenmiş IQ kaynağından bounded ortalama güç varsa kayıt oluşturur;
kaynak yoksa başarısızlık açıkça yazılır. Elle yazılan güç ise `MANUEL GÜÇ
GİRDİSİNİ KAYDET` ile ayrı kaynak etiketiyle saklanır.

`YÖN` sekmesindeki `Harita` görünümü hedef konumu hesaplamaz. `Eğitim Senaryosu
Yükle` ile `Baş 0° + bağıl 75° = coğrafi 75°` veya `Baş 300° + bağıl 75° =
coğrafi 15°` senaryosunu seçin. Çizgi yalnız tahmini geliş doğrultusunu gösterir;
uçta hedef işareti yoktur. Baş/yön referansı kutusu kapalıysa uygulama yalnız
`Bağıl yön — coğrafi azimut referansı yok` durumunu gösterir ve coğrafi LOB çizmez.
Varsayılan `Harita (internet)` sağlayıcısı anahtarsız OpenFreeMap stilini açar.
İnternet yoksa uygulama doğru biçimde çevrimdışı/yedek görünüme düşer. Farklı,
meşru bir MapLibre stili gerekiyorsa aşağıdaki ortam değişkeniyle değiştirilebilir:

```powershell
$env:TEKNOFEST_MAP_STYLE_URL = "https://tiles.openfreemap.org/styles/liberty"
python -B -m host.operator_console
```

Google uydu görünümü yalnız kullanıcının `TEKNOFEST_GOOGLE_MAPS_API_KEY` ortam
değişkeniyle etkinleşir; anahtar repoya yazılmaz. Yarışma alanı çevrimdışı
çalışacaksa `host/operator_console/map_assets/README.md` içindeki PMTiles ve
stil yerleştirme yönergesini uygulayın. QWebEngine, harita verisi veya yapılandırma
bulunmazsa konsol çalışmaya devam eder ve Türkçe metinsel fallback gösterir.

### Saha konumu ve manuel anten kabulü

1. `KONUMUMU AL` yalnız operatör düğmeye bastıktan sonra Qt/işletim sistemi
   konum sağlayıcısından tek seferlik fix ister. Başarı varsa kaynak `BİLGİSAYAR`
   ve varsa doğruluk metre cinsinden görünür.
2. Bu bilgisayarda sağlayıcı fix döndürmez veya izin vermezse uygulama
   `Bilgisayar konumu alınamadı. Manuel konum girebilirsiniz.` yazar; koordinat
   uydurmaz.
3. Enlem/boylamı girip `MANUEL KONUMU KULLAN` seçin. Kaynak `MANUEL`, doğruluk
   `bilinmiyor` olur; bu durum LIVE GNSS değildir.
4. `LIVE GNSS (rezerve — bağlı değil)` yalnız görünür bir geleceğe ayrılmış
   durumdur, seçilemez ve canlı konum iddia etmez.
5. Anteni kontrollü ve izinli alıcı düzeninde elle seçilen açıya çevirin,
   `ANTEN AÇISI (MANUEL)` alanına o açıyı girin ve `GÜÇ ÖLÇ` ile kaydedin.
   Her satır açı, coğrafi azimut (varsa), güç ve kaynak gösterir.
6. Coğrafi LOB yalnız geçerli konum ve açıkça girilmiş sıfır referansı varsa
   çizilir. Çizginin sonu hedef ya da konum kestirimi değildir.

Yalnız offline laboratuvar bileşimindeki `ET` sekmesinde varsayılan `OFFLINE`
modda tekli/çoklu/barrage
seçilip sürekli karıştırma önizlemesi başlatılabilir. Analog aldatma alanında
scenario ve FM/NFM seçilerek taban bant/spektrum önizlemesi görülebilir. Kilitli
modlar RF göndermez. Bu sekme ürün uygulamasında ve yayın paketinde bulunmaz.
`ACİL DURDURMA` fail-closed durumu kilitler.

## Vivado görsel inceleme

Önce proje yoksa üretin:

```text
C:\AMDDesignTools\2025.2\Vivado\bin\vivado.bat -mode batch -source scripts/create_p0_vivado_project.tcl
```

Ardından Vivado 2025.2'de `build/p0/vivado/p0_runtime.xpr` dosyasını açın.

1. Flow Navigator → IP Integrator → Open Block Design → `p0_system`.
2. `processing_system7_0`, `axi_dma_0`, `p0_dsp_runtime_0`, iki AXI interconnect,
   `proc_sys_reset_0` ve `irq_concat` bloklarını görün.
3. MM2S'nin DSP `S_AXIS` girişine, DSP `M_AXIS` çıkışının S2MM'ye, DMA memory-map
   masterlarının PS `S_AXI_HP0`/DDR yoluna ve iki DMA interruptının `IRQ_F2P`ye
   bağlı olduğunu izleyin.
4. Flow Navigator → Open Synthesized Design → Schematic.
5. `p0_system_i/p0_dsp_runtime_0/inst/core` hiyerarşisini açın; `hann`,
   `fft_wrapper`, `fft` ve `power` örneklerini görün.

Blok tasarımı, sentez veya bitstream kartta çalıştırılmış DMA anlamına gelmez.
