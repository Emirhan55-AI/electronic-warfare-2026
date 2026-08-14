# ADR-0008 — Operatör Destekli Temel Parametre Ölçümü

## Protokol düzeltmesi: independent-fields-v2

İlk frozen koşu, otomatik spanı bütün manuel alanların global kapısı yaptığı ve OBW edge/temporal kontrollerini diğer alanlara bağladığı için capability kararı olarak geçersizdir. Bu koşu `invalid-protocol-run1` altında hash-bağlı biçimde korunur. Algoritma kimlikleri, sayısal eşikler, sahneler, seed'ler ve paydalar değiştirilmeden alan kararları ayrıştırılmıştır. Otomatik span geçmese bile bağımsız binding ve OOS kapılarını geçen manuel alanlar capability profilinde yer alabilir; bu durum PHASE-04 tamamlanma iddiası değildir.

## Karar

PHASE-04-E1, PHASE-03 tarafından doğrulanmış bir olay için operatörün açıkça onayladığı sabit analiz aralığında alan bazlı ölçüm yapar. Otomatik aralık yalnız kolaylıktır; başarısız olması manuel aralığı tek başına kapatmaz. Operatör truth frekansı, beklenen bant, güç veya sınıf giremez.

Frekans iki ayrı kavramdır: `Yayın Merkez Frekansı`, debiased spektral gücün birinci momentidir; `Taşıyıcı Çizgisi Frekansı` yalnız yeterli çizgi kanıtında yayımlanır. Çizgisiz veya bastırılmış taşıyıcılı bir yayında spektral merkez taşıyıcı gibi gösterilmez.

OBW99 hesabı `max(PSD-noise, 0)` toplamını kullanmaz. Ortalama PSD'den bin başına noise çıkarılır; pozitif toplam excess, toplamı değiştirmeden non-negative simplex üzerine projekte edilir. Kümülatif `%0,5/%99,5` kenarları bu projected güçten alınır. Kanal gücü signed toplam excess üzerinden entegre edilir. Bu seçim saf gürültü binlerinin rectification bias üretmesini önler.

Her capability binding ve OOS kapılarını bağımsız geçer. Profil yalnız geçen alanları taşır; hiçbir sonuç `PHASE-04 tamamlandı` anlamına gelmez. Ortak evidence/hash bağı veya worker güvenliği bozulursa E1 katmanı kapanır ve byte-sabit PHASE-03 `regional` profiline dönülür.

## Sınırlar

- Dört ardışık frame ve açık `Ölçümü Başlat` eylemi zorunludur.
- Frame okuma ve ölçüm tek bounded worker'dadır; UI thread'inde DSP yapılmaz.
- Sonuçlar kayıtlı/sentetik I/Q ve operatörce seçilmiş izole span ile sınırlıdır.
- Güç `dBFS/bin` ve `dBFS` olarak kalır; dBm veya RF giriş gücü değildir.
- Analog/Sayısal sonucu yalnız frozen sentetik ailelerde sınırlı, açıklanabilir ayrımdır; modülasyon tanıma değildir.
- D1 başarısızlığı ve R1/R2 evidence yeniden etiketlenmez veya değiştirilmez.
