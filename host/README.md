# Ana Sistem Yazılımı

`operator_console/`, yarışmada kullanılacak kalıcı Türkçe Windows operatör uygulamasının PHASE-02 sürümüdür. PySide6, Qt Widgets ve pyqtgraph kullanarak seçilen SigMF kaydının metadata özetini, gerçek referans spektrumunu ve bounded waterfall geçmişini gösterir.

Uygulama yalnız kayıtlı veri incelemesini destekler. HackRF, ZedBoard, FPGA, sinyal tespiti veya TX bağlantısı içermez ve bunlara ait sahte durum göstermez. Dosya okuma ile FFT tek görevli worker'da yürütülür; UI thread'i yalnız sunum yapar.

Kaynak çalıştırma:

```text
python -m host.operator_console
```
