# P0 Offline Doğrulama ve Operatör Kullanımı

## Offline doğrulama uygulaması

Repository kökünde çalıştırın:

```text
python -B scripts/run_p0_demo.py
```

Bu tarihsel script adı yalnız doğrulama uyumluluğu için korunur; kurduğu uygulama
`app.operator_console.laboratory` bileşimidir ve yayın paketi dışındadır.

Gerçek SigMF/HackRF kaynaklarıyla açılan kanonik ürün komutu:

```text
python -B -m app.operator_console
```

Ürün komutu test, eğitim veya offline ET değeri yüklemez. `SigMF Kaydı`
seçiliyken `SigMF Aç` ile metadata
dosyası açılır; doğrulanmış tespit seçimi `PARAMETRELER` ve `Dinleme` sekmeleri
arasında aynı olay kimliğiyle korunur.

İlk sekmede deterministik replay spektrumu, waterfall geçmişi ve doğrulanmış P0
OS-CFAR sonucu görünür. `GÖREV` bölümündeki üç hakem girişi de aynı işleme
zincirini kullanır: IQ → periyodik Hann → FFT → OS-CFAR + geniş bant kurtarma → 2/3 zamansal onay →
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
50 kHz pencere toplar ve aynı çok ölçekli tespit/zamansal onay zincirini çalıştırır.
`100.200` MHz yanlış frekans girişi sinyal üretmez.

Üç olumlu senaryonun replay çıktısı, arayüz yuvarlamasıyla şöyledir:

- emisyon merkez frekansı: `100.090003 MHz`
- alt/üst sınır: `100.088875` / `100.091125 MHz`
- gerçek bant genişliği: `2.250 kHz`
- kaba aday bant genişliği: `3.250 kHz`
- göreli güç: `-4.44 dBFS` ve `KALİBRE EDİLMEMİŞ · dBFS`
- SNR: `35.63 dB`
- sınıf: `Analog`
- kaynak: `REPLAY`

`PARAMETRELER` sekmesinde emisyon merkez frekansı, gürültü/eşik referanslı gerçek bant, göreli
dBFS, SNR, Analog/Sayısal sonucu, backend ve kaynak görünür. Güç alanı
`KALİBRE EDİLMEMİŞ · dBFS` yazar.

`Yön Bulma` çalışma alanında operatör anteni kendi seçtiği başlangıç yönüne
getirir. Tek düğmenin ilk başarılı ölçümü bu konumu bağıl `0°` sayar. Uygulama
sonraki hedefi otomatik olarak saat yönünde `15°`, `30°`, …, `345°` biçiminde
gösterir; operatör anteni gösterilen konuma getirip sabitledikten sonra aynı
düğmeye basar. Her başarılı kayıt seçili kanalın dört gerçek I/Q karesinden
üretilmiş PL/ARM dBFS gücünü taşır. Süre aşımı veya iptal açıyı ilerletmez.

Ürün serbest açı, gerçek kuzey, harita, hedef konumu veya coğrafi kerteriz
sunmaz. Uygulama pusula, IMU veya enkoderden anten yönü çıkarmaz ve dönüş hızını
açıya çevirmeye çalışmaz. 24 açılık tur sonunda yalnız bağıl tepe yönü; tepe ve
ön/arka kalite kapıları geçerse gösterilir. Fiziksel derece doğruluğu ancak
bilinen bağıl açılı kontrollü anten deneyiyle kabul edilebilir.

Ana ürün kabuğu yalnız ED görevlerini sunar. ET alanı, ET görev modelleri ve RF
TX arka ucu ADR-0044 kapsam kararıyla kaldırılmıştır. Tarihsel ET kanıtları bu
demo akışında yüklenmez ve güncel ürün yeteneği sayılmaz.

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
