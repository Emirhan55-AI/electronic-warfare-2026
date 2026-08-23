# APP-E Arayüz Teknolojisi Doğrulaması

Bu dizin ürün paketine girmez. Aynı doğrulanmış SigMF fixture'ından çıkarılan
spektrum verisini Qt Widgets ve Qt Quick/QML sunum katmanlarına vererek yalnız
arayüz teknolojisi kararını ölçer.

Prototip ekranındaki değerler ürün verisi değildir ve operatör uygulamasında
gömülü kaynak olarak kullanılmaz. Girdi kimliği ile hash değeri kanıt kaydında
yer alır.

Çalıştırma:

```powershell
python -B scripts/verify_app_e_ui_technology.py --write
python -B scripts/verify_app_e_ui_technology.py --check
```
