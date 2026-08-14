# ADR-0007 — İşgal Edilen Bant Genişliği Semantiği

## Durum

Accepted

Bu karar ve beraberindeki sayısal kapılar kullanıcı tarafından onaylanmıştır. Bu ADR, tek başına yöntem uygulaması veya yetenek doğrulaması değildir.

## Bağlam

Şartname, Elektronik Destek görevi kapsamında bant genişliğinin çıkarılmasını ister; ancak bant genişliği türünü, ölçüm yöntemini veya sayısal hata toleransını tanımlamaz. Eski KTR yaklaşımı yerel gürültü eşiğini aşan spektral zarfı kullanıyordu. PHASE-04-R1 ve PHASE-04-R2 ise nominal ya da fiziksel olarak gerekli bant tanımlarıyla karşılaştırılan açıklanabilir zarf yöntemlerini sınadı ve bağlayıcı kapıları geçemedi.

Bu başarısızlık kanıtları korunacaktır. R1/R2 sonuçları geriye dönük olarak OBW99 başarısızlığı şeklinde yeniden adlandırılmayacaktır; çünkü o çalışmaların ground truth ve ölçüm semantiği OBW99 değildi.

## Karar

Kanonik ve mevcut sistemle ölçülebilir bant çıktısı `%99 İşgal Edilen Bant Genişliği (OBW99)` olacaktır. OBW99, gürültü çıkarılmış gözlenen spektral güçte toplam excess gücün alt `%0,5` ve üst `%0,5` kümülatif noktaları arasında kalan frekans aralığıdır.

Aşağıdaki kavramlar birbirinden ayrıdır:

| Kavram | Anlam | D1 kapsamı |
|---|---|---|
| OBW99 | Gözlenen ve ölçüm kalitesi yeterli yayının toplam excess gücünün `%99` bölümünü kapsayan aralık | Kanonik ölçülebilir çıktı |
| Gerekli bant genişliği | Belirli bir emisyonun gerekli bilgi ve kaliteyle taşınması için fiziksel/standart temelli bant | Uygulanmayacak |
| Nominal/kanal bant genişliği | Kanal planı, ekipman veya protokol tarafından tanımlanan ayrılmış/deklare bant | Uygulanmayacak |
| KTR eşik zarfı | Yerel gürültü eşiği üstündeki gözlenen spektral destek | Tarihsel yöntem; OBW99 değildir |

OBW99 kararı, gerekli ya da nominal bant genişliğini tahmin ettiği anlamına gelmez. Aynı şekilde tek bir yayın ailesinde elde edilen sonuç, bütün sinyal türlerinde genel doğruluk iddiası oluşturmaz.

## Yetenek sınırı

Planlanan profil kimliği `phase04d1-occupied-bandwidth-capability` olacaktır. Bu profil tam PHASE-04 profili değildir; yalnız şu zinciri kapsar:

1. PHASE-03 `regional` tespiti,
2. yayın/candidate izolasyonu,
3. OBW99 alt sınırı,
4. OBW99 üst sınırı,
5. OBW99 genişliği,
6. gözlem, temporal durum ve kalite nedeni.

Taşıyıcı, spektral merkez, güç/SNR, analog/sayısal ayrımı, gerekli bant ve nominal bant bu capability profilinin kapılarına girmez ve sayısal sonuç üretmez. Doğru başarı ifadesi şudur:

> OBW99 bant genişliği yeteneği doğrulandı; PHASE-04'ün diğer parametreleri açık.

Bu ifade ancak önceden kilitlenmiş binding benchmark ve yöntemden bağımsız kilitli OOS kapılarının tamamı geçerse kullanılabilir. Herhangi bir bağ veya digest bozulursa bütün PHASE-04 katmanı kapanır ve Operasyon uygulaması saf PHASE-03 tespit profiline döner.

## Runtime ve arayüz sınırı

Capability bağı kurulursa çalışma zinciri `PHASE-03 regional detection + D1 OBW99` olur. Arayüzde yalnız aşağıdaki alanlar etkinleşebilir:

- İşgal Edilen Bant Genişliği,
- Alt Bant Sınırı,
- Üst Bant Sınırı,
- Ölçüm: `%99 güç`,
- gözlem/temporal durum,
- kalite nedeni.

Gerekli/nominal bant, taşıyıcı, güç/SNR ve analog/sayısal ayrımı sayı göstermez; `Henüz doğrulanmadı` durumunda kalır. Kullanıcıya genel bir “PHASE-04 başarılı” mesajı gösterilmez.

Durum semantiği şöyledir:

- Capability uygulanmamış veya devre dışıysa sonuç üretilmez ve profil düzeyinde `Henüz doğrulanmadı` gösterilir.
- Yayın gözlenmediyse `not_observed` kullanılır.
- Ölçüm denenmiş ancak kalite yetersizse `insufficient_quality` kullanılır.
- Yayın izolasyonu veya sınır clipping'i güvenilir değilse `uncertain` kullanılır.
- Bir ölçüm kavramsal olarak uygulanabilir değilse `not_applicable` kullanılır.

Mevcut public enum bu ayrımı karşılar; yalnız dilsel kolaylık için yeni enum eklenmeyecektir.

## Referans ve kabul sınırı

Clean OBW99 ground truth, analitik Carson/RRC/nominal formüllerden türetilmeyecektir. Aynı örnekleme hızındaki uzun, gürültüsüz ve deterministik I/Q; PHASE-02 ile aynı Hann ve güç normalizasyonu üzerinden çok-frame ortalama PSD'ye dönüştürülecektir. Sıfır doldurma yalnız frekans kenarı interpolasyonunu inceltir; yeni fiziksel bilgi üretmez.

Sayısal kapılar şartname gereği değildir. Bunlar ölçüm doğruluğu, abstention dürüstlüğü ve yetenek sınırını korumak için kabul edilen proje içi mühendislik kapılarıdır. Kesin sözleşme [OCCUPIED_BANDWIDTH_CONTRACT.md](../interfaces/OCCUPIED_BANDWIDTH_CONTRACT.md), `acceptance-gates.json` ve `reference-contract.json` dosyalarında yer alır. Değerler estimator sonucuna göre değiştirilmeyecektir.

## Sonuçlar

- R1/R2 katalogları, method-lock dosyaları ve evidence değişmeden kalır.
- D1 başarısı diğer PHASE-04 alanlarının başarısı sayılmaz.
- D1 kapıları geçmezse yeni estimator yarışı, eşik ayarı veya yeni kurtarma döngüsü başlatılmaz; başarısızlık kanıtı yazılır ve kullanıcı kararı beklenir.
- Gerçek ISM kaydı annotation içermediği için bant doğruluğu kanıtı değildir; yalnız bounded çalışma, determinizm ve çıktı kararlılığı gösterebilir.
- Bu karar canlı HackRF, dBm, FPGA, saha performansı veya bütün yayın türlerinde doğruluk iddiası oluşturmaz.

## Kaynaklar

- [ITU-R SM.328-12 — Emisyonlar ve bant genişliği tanımları](https://www.itu.int/dms_pubrec/itu-r/rec/sm/R-REC-SM.328-12-202509-I%21%21PDF-E.pdf)
- [ITU-R SM.443-4 — İşgal edilen bant genişliği ölçümü](https://www.itu.int/dms_pubrec/itu-r/rec/sm/R-REC-SM.443-4-200702-I%21%21PDF-E.pdf)
- [ITU-R SM.1541-7 — İstenmeyen emisyon sınırları için bant genişliği kavramları](https://www.itu.int/dms_pubrec/itu-r/rec/sm/R-REC-SM.1541-7-202409-I%21%21PDF-E.pdf)
