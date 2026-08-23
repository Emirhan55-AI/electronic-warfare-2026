# ADR-0027: Operatör QML Çalışma Zamanı Mimarisi

- Durum: **Accepted**
- Karar tarihi: 2026-08-24
- İlgili paket: APP-F

## Bağlam

ADR-0026 sunum katmanı için Qt Quick/QML'i, kaynak ve doğrulanmış işleme
sözleşmeleri için Python/PySide6'yı seçti. Eski QWidget denetleyicisi görünür
öğelere doğrudan bağlı olduğu için yeni sunuma taşınması katman sınırını ve ürün
paketi sadeliğini bozuyordu.

Ürün uygulaması yalnız operatörün seçtiği SigMF kaydını veya gerçek HackRF RX
backend'ini kullanmalıdır. Worker sonucu beklenirken arayüz iş parçacığı
engellenmemeli; eski kaynak sonucu yeni kaynak durumuna yazılmamalıdır.

## Karar

`app.operator_console.__main__`, Qt Quick ürün bileşimini başlatır. QWidget
bileşimi tarihsel arayüz ve algoritma regresyonları için `build_application`
üzerinden erişilebilir kalır, fakat ürün başlangıcında içe aktarılmaz.

`OperatorViewModel` aşağıdaki sınırlara sahiptir:

- tek worker ve en fazla bir bekleyen son-kare isteği;
- kaynak değişiminde generation anahtarıyla eski sonucun reddi;
- SigMF sözleşme denetimi ve HackRF araç/cihaz denetiminin GUI dışı yürütümü;
- doğrulanmış `RuntimePipeline` ile FFT, OS-CFAR ve temporal olay üretimi;
- seçili doğrulanmış olay için yalnız açık operatör eyleminden sonra P0 parametre
  ölçümü;
- QML sınırında viewport genişliğine göre en fazla 1600 spektrum noktası;
- yön bulma gücünün yalnız etkin gerçek I/Q karesinden kaydedilmesi.

QML, bilimsel 4096-bin sonucu değiştirmez. Çizim için her yatay dilimde maksimum
değer korunarak indirgeme yapılır. Spektrogram geçmişi 48 satırla sınırlıdır.

## Dürüst özellik kapıları

Ürün navigasyonunda bağlı olmayan GNSS, hedef konumu, faz uyumlu çok kanallı DoA,
TX ve offline eğitim kontrolleri bulunmaz. Analog dinleme referans zinciri ve WAV
kanıtı repository'de korunur; yeni ürün bileşiminde sürekli gerçek kaynak ve ses
aygıtı kabulü tamamlanmadığı için çalışır bir kontrol gibi sunulmaz. Coğrafi
harita da doğrulanmış konum çözümü ve yeni sunum bağlantısı olmadan gösterilmez.

## Sonuçlar

- Ürün başlangıcı QWidget, laboratuvar, offline ET veya doğrulama fixture modülü
  yüklemez.
- QML dosyası deploy tanımına eklenir; Qt Quick/QML modülleri paketlenir.
- Tam C++ yeniden yazımı yapılmaz. Darboğaz kararı ölçüm kanıtı gerektirmeye devam
  eder.
- Mevcut bilgisayardaki offscreen yazılım çizimi sonucu hedef GPU veya saha
  bilgisayarı performans iddiası değildir.
