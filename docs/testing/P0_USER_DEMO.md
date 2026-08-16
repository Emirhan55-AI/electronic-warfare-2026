# P0 Kullanıcı Demosu

## Operatör demosu

Repository kökünde çalıştırın:

```text
python -B scripts/run_p0_demo.py
```

İlk sekmede deterministik replay spektrumu, waterfall geçmişi ve doğrulanmış P0
OS-CFAR sonucu görünür. `GÖREV` bölümündeki üç hakem girişi de aynı işleme
zincirini kullanır: IQ → periyodik Hann → FFT → OS-CFAR → 2/3 zamansal onay →
parametre çıkarımı. Arayüz MHz kabul eder; işleme katmanı yalnızca Hz kullanır.

### Demo A — bilinmeyen frekans

1. `Bilinmeyen Frekans` kipini seçin.
2. `Taramayı Başlat` düğmesine basın.
3. Tek bir onaylı sinyal ve aşağıdaki ortak sonuçların görüntülendiğini doğrulayın.

### Demo B — hakem bant bildirdi

1. `Hakem Bant Bildirdi` kipini seçin.
2. Alt sınırı `100.080`, üst sınırı `100.100` MHz girin.
3. `Taramayı Başlat` düğmesine basın ve sinyalin bulunduğunu doğrulayın.

Ters sınırlar, 20 MHz'den geniş bantlar ve 1 MHz–6 GHz alıcı sınırı dışındaki
girişler reddedilir. `99.950`–`99.960` MHz dışlama bandı sinyal üretmez.

### Demo C — hakem frekans bildirdi

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

`YÖN BULMA` sekmesinde 0/30/60/90/120 derece fixture noktaları, açı–güç eğrisi ve
60 derece ham maksimum LOB görünür. Yeni açı/güç girip `Ölçüm Noktasını Kaydet`
düğmesiyle aynı veri modeline nokta eklenebilir.

`ET · KONTROLLÜ TEST` sekmesinde varsayılan `OFFLINE` modda tekli/çoklu/barrage
seçilip sürekli karıştırma önizlemesi başlatılabilir. Analog aldatma alanında
scenario ve FM/NFM seçilerek taban bant/spektrum önizlemesi görülebilir. Kilitli
modlar RF göndermez. `ACİL DURDURMA` fail-closed durumu kilitler.

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
