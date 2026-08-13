# Ana Sistem Yazılımı

`operator_console/`, kalıcı Türkçe Windows operatör uygulamasının PHASE-04 sürümüdür. PySide6, Qt Widgets ve pyqtgraph kullanarak seçilen SigMF kaydının metadata özetini, gerçek referans spektrumunu, bounded waterfall geçmişini, uyarlanabilir eşiği, kaba adayları, temporal olayları ve validated profil varsa kalibre edilmemiş çekirdek parametreleri gösterir.

Uygulama yalnız kayıtlı veri incelemesini destekler. Detector, gruplama, temporal ve parametre katmanları allowlist içindeki doğrulanmış profilden kurulur. PHASE-04 comparison/digest bağı geçersizse parametre katmanı yüklenmez, sayısal alanlar ve bant katmanı temizlenir ve uygulama dürüstçe PHASE-03 tespit profiline döner. Kaynak okuma, FFT, tespit ve parametre çıkarımı tek görevli worker'da yürütülür; UI thread'i yalnız sunum yapar. Frame-local bant görünümü kesintisiz kanal alıcısı değildir. Güç dBFS'tir, dBm değildir. HackRF, ZedBoard, FPGA veya TX bağlantısı içermez.

Kaynak çalıştırma:

```text
python -m host.operator_console
```
