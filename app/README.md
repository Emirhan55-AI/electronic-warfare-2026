# Operatör Uygulaması

`operator_console`, PySide6 ve Qt Quick/QML ile geliştirilen Türkçe masaüstü
uygulamasıdır. Ürün çalışma zamanı yalnız operatörün seçtiği SigMF kaydını veya
gerçek HackRF RX kaynağını kabul eder. Test backend'leri, kayıtlı doğrulama
verileri ve çevrimdışı ET araçları ürün paketine dahil edilmez.

Uygulamanın mevcut çalışma alanları:

- `Spektrum`: kaynak yönetimi, dBFS spektrum, spektrogram, zamansal tespitler ve
  operatör onaylı sinyal parametre ölçümü.
- `Yön Bulma`: gerçek I/Q gücünün elle girilen anten açısıyla kaydı, bağıl geliş
  açısı ve geçerli referans varsa kerteriz.
- `Sistem`: çalışma zamanı bileşen durumu, ölçülen host işlem süresi ve olaylar.

Parametre ölçümü yalnız doğrulanmış bir tespit, dört ardışık gözlem ve operatörün
onayladığı analiz aralığı bulunduğunda açılır. Sonuçlar kalibrasyonsuz dBFS
ölçeğindedir; uygulama dBm, çok kanallı DoA, menzil veya otomatik hedef konumu
üretmez.

Çalıştırma:

```powershell
python -m app.operator_console
```

Ürün sınırı `config/app/product-package.json`, arayüz kabul koşulları ise
`scripts/verify_app_f_release_ui.py` tarafından denetlenir.
