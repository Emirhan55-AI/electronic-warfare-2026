# P0 Kullanıcı Demosu

## Operatör demosu

Repository kökünde çalıştırın:

```text
python -B scripts/run_p0_demo.py
```

İlk sekmede deterministik replay spektrumu, waterfall geçmişi ve doğrulanmış P0
OS-CFAR sonucu görünür. `PARAMETRELER` sekmesinde taşıyıcı, eşik referanslı bant,
göreli dBFS, SNR, Analog/Sayısal sonucu, backend ve `HOST REFERENCE` kaynağı
görünür. Güç alanı `KALİBRASYON BEKLİYOR` yazar.

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
