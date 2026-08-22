# ADR-0024 — Ürün ve Doğrulama Çalışma Zamanı Sınırı

- Durum: Kabul edildi
- Tarih: 2026-08-23
- İş paketi: APP-C

## Bağlam

Operatör uygulamasının önceki bileşimi; gerçek SigMF ve HackRF kaynaklarıyla aynı
giriş noktasında deterministik mock backend, sentetik yön bulma eğitimi ve offline
ET doğrulama konsolu sunuyordu. Bu yapı testlerin çalışmasını kolaylaştırsa da
yayın uygulamasının yetenek sınırını belirsizleştiriyor ve doğrulama fixture'larının
ürün paketine sürüklenmesine izin veriyordu.

## Karar

Kanonik ürün giriş noktası `host.operator_console.__main__` yalnız `SigMF Kaydı`
ve `HackRF Canlı RX` kaynaklarını oluşturur. Ürün bileşimi:

- `DeterministicMockBackend` sınıfını import etmez,
- sentetik DF fixture modülünü import etmez,
- offline ET modellerini veya ET navigasyonunu oluşturmaz,
- yerleşik demo/video verisi ya da hardcoded kayıt yolu kullanmaz.

Doğrulama bileşimi `host.operator_console.laboratory` altında ayrı giriş kurar.
Mock backend, eğitim sahneleri ve TX-kilitli offline ET yalnız bu açık laboratuvar
bileşiminde yüklenir. Gerçek-kayıt analizleri ürün tarafında yalnız operatörün
seçtiği SigMF/JSON dosyaları üzerinden çalışabilir.

`config/app/product-package.json` yayın kapsamını, `pysidedeploy.spec` ise yasaklı
laboratuvar importlarını tanımlar. Runtime import testi ürün oluşturulduğunda bu
modüllerin `sys.modules` içinde bulunmadığını doğrular.

## Sonuçlar

- Test ve golden kaynakları repository'de korunur fakat ürün paketi dışındadır.
- Laboratuvar araçlarının kaldırılması gerekmez; sahiplikleri ve giriş noktaları
  ürün uygulamasından ayrıdır.
- Dizinlerin `app/`, `algorithms/`, `platform/`, `verification/` olarak fiziksel
  taşınması APP-D kapsamındadır; bu ADR o taşımanın bağımlılık yönünü dondurur.
- ET/RF TX yeteneği uygulanmış veya fiziksel olarak doğrulanmış sayılmaz.
