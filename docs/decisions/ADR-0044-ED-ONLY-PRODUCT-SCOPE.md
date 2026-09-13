# ADR-0044 — Yalnız ED Ürün Kapsamı

- Durum: Kabul edildi
- Tarih: 13 Eylül 2026
- Kapsam: Ürün arayüzü, kaynak kodu, paketleme ve doğrulama
- Önceki kararlar: ADR-0023, ADR-0041 ve ADR-0043

## Bağlam

Kullanıcı, elektronik taarruz işlevlerinin tamamının arayüzden ve depodaki
uygulamadan kaldırılmasını; geliştirmeye yalnız elektronik destek sistemiyle
devam edilmesini istemiştir.

## Karar

Ürün ve laboratuvar arayüzleri yalnız ED işlevlerini sunar. ET çalışma alanı,
alan seçimi, görev eylemleri, TX çalışma zamanı, dalga biçimi üreticileri,
cihaz profili, paketleme girdileri, yürütülebilir doğrulayıcılar ve ET'ye özel
testler depodan kaldırılmıştır. PHASE-10–12 etkin geliştirme planından
çıkarılmıştır. PHASE-13 yalnız ED bütünleştirme ve demo kapsamındadır.

KTR-5.1–5.4 kaynak gereksinim kimlikleri izlenebilirlik tablosunda korunur,
ancak kullanıcı kararıyla ürün kapsamı dışında ve uygulanmıyor durumundadır.
Bu satırlar yeniden geliştirme yetkisi oluşturmaz.

## Tarihsel Kayıt Sınırı

Önceki ADR'ler, tarihli inceleme ve ölçüm çıktıları geçmişte yapılan çalışmanın
değişmez kaydı olarak korunur. Bunlar güncel kodun yeteneği, çalıştırılabilir
test veya yeniden açılmış ET fazı değildir. Önceki laboratuvar ortamı onayı da
güncel üründe TX yolu bulunduğu anlamına gelmez.

## Sonuç

Güncel kaynakta RF yayın arka ucu yoktur. ED tespit, parametre çıkarımı,
dinleme ve yön bulma akışlarının mevcut kabul kapıları değişmeden açık kalır;
ET kaldırılması bu kapıların geçtiği anlamına gelmez.
