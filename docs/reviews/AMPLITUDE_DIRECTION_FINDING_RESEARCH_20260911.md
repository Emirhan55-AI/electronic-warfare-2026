# Genlik Tabanlı Yön Bulma: Bilimsel Temel ve Ürün Mimarisi

## Karar

KTR §5.1.4 için seçilen yöntem genlik tabanlı yön bulmadır. İlk ürün hedefi,
tek sensör noktasında uygun yönlü antenin elle döndürülmesi ve aynı doğrulanmış
RF kanalında ölçülen güçlerin karşılaştırılmasıdır. Sonuç bir **kerteriz** veya
Line of Bearing (LOB) olur. Tek ölçüm noktasından menzil ya da verici konumu
üretilmez.

KrakenSDR doğrudan algoritma temeli değildir. KrakenSDR beş eşzamanlı ve faz
uyumlu alıcı kanalı, anten dizisi geometrisi, kanal kalibrasyonu ve MUSIC/
Root-MUSIC gibi uzaysal yöntemler kullanır.[^1] Tek HackRF ve sırayla döndürülen
yönlü antende eşzamanlı kanalların çapraz korelasyon matrisi bulunmadığı için
bu yöntemlerin sonuçlarını taklit etmek bilimsel olarak geçersiz olur. KrakenRF
yazılımından alınabilecek yararlı ürün ilkeleri hedef kanal seçimi, squelch/
kalite kapısı, ayarların kayıt altına alınması, gecikme ölçümü ve harita üzerinde
kerteriz sunumudur.[^2]

## Ölçüm modeli

Kompleks taban bant örneği `z[n] = I[n] + jQ[n]` için bir anten açısındaki
sayısal güç doğrusal alanda hesaplanır:

`P(θ_i) = (1/N) Σ |z_i[n]|²`

FFT alanında eşdeğer ölçüm, yalnız hedef kanalına karşılık gelen hücrelerin
doğrusal güçlerinin toplamıdır:

`P_ch(θ_i) = Σ_{k∈K_ch} P_i[k]`

Gösterim değeri tam ölçeğe göre göreli güçtür:

`P_dBFS(θ_i) = 10 log10(P_ch(θ_i) / P_FS)`

Burada mutlak dBm gerekmez. Yön hesabı aynı alıcı, merkez frekansı, örnekleme,
LNA/VGA, kanal genişliği ve sayısal ölçek korunarak yapılan **göreli** güç
karşılaştırmasına dayanır. Tekrarlı dB değerlerinin aritmetik ortalaması fiziksel
güç ortalaması değildir; tekrarlar önce doğrusal güce çevrilir, ağırlıklı
ortalama alınır ve sonuç yeniden dB'ye çevrilir.

KTR'nin tanımladığı zorunlu kestirim, ölçülmüş açılar arasındaki ham maksimumdur:

`θ_hat = argmax_{θ_i} P_ch(θ_i)`

Ürün bilinmeyen anten desenine parabol veya spline uydurarak ölçülmemiş bir
hassas açı üretmez. Anten deseni frekansa göre fiziksel olarak kalibre edilirse
desen eşleme daha sonra ayrı bir yöntem/profil olarak değerlendirilebilir.

## Açısal örnekleme

Ham maksimum yönteminde ideal ve eşit aralıklı açı ızgarasının tek başına
oluşturduğu kuantalama RMS değeri, gerçek yönün iki örnek arasında düzgün
dağıldığı varsayımıyla `Δθ/√12` olur. Bu değer anten, gürültü ve çok yollu yayılım
hatalarını içermez.

| Açı adımı | Açı sayısı | İdeal ızgara RMS | Sayısal sahne RMS | En büyük sayısal hata |
|---:|---:|---:|---:|---:|
| 45° | 8 | 12,990° | 12,987° | 22° |
| 30° | 12 | 8,660° | 8,670° | 15° |
| 15° | 24 | 4,330° | 4,378° | 8° |

Bu nedenle sekiz açılı 45° tarama güvenilir bir kaba arama olabilir, fakat nihai
RMS sonucu için yeterli ürün varsayılanı değildir. Güncel saha profili 0°–345°
arasında 15° adımlı 24 farklı açı ister. Tablo,
[`amplitude-df-numeric-v1.json`](../../results/evidence/phase09/amplitude-df-numeric-v1.json)
kanıtından yeniden üretilebilir.

## Sonuç vermeme kapıları

Bir maksimumun bulunması tek başına güvenilir kerteriz anlamına gelmez. Ürün
aşağıdaki koşullarda LOB yayımlamaz:

- 24 farklı açı veya tam 360° kapsama yoksa,
- komşu ana lob çevresi dışında belirgin rakip bir tepe varsa ve ana tepe
  belirginliği 3 dB'nin altındaysa,
- ölçülen karşı yöndeki güç ana tepeden en az 3 dB düşük değilse,
- merkez frekansı hedef kanal genişliğinin yarısından fazla kaymışsa,
- merkez frekansı, örnekleme, kanal hücreleri veya LNA/VGA bağı değişmişse,
- aynı kaynak karesi ikinci bir fiziksel açı ölçümü gibi tekrar kullanılmışsa.

3 dB kapıları yarışmanın resmî doğruluk eşiği değildir. Bunlar ilk fail-closed
mühendislik profilidir ve yalnız bağımsız saha verisiyle sürümlenebilir.
Karşı yön kapısı, yönlü antenlerde görülebilen ön/arka lob belirsizliğinin
yanlış kesin kerterize dönüşmesini engeller. Literatürde genlik karşılaştırma
hatalarının anten yöneltme, kanal kazanç uyumsuzluğu, frekansa bağlı huzme
genişliği, SNR ve polarizasyondan etkilendiği; kalibrasyon tablolarının bu
hataların bir bölümünü azaltabildiği gösterilmektedir.[^3][^4]

## RMS doğruluk hesabı

Her fiziksel koşu için işaretli dairesel hata kullanılır:

`e_i = wrap180(θ_hat,i − θ_true,i)`

`RMSE_deg = sqrt((1/M) Σ e_i²)`

Örneğin 359° ile 1° arasındaki hata 358° değil 2°'dir. ITU-R SM.2125 sistem
doğruluğunu gerçek azimut ile gösterilen kerteriz arasındaki farkın RMS değeri
olarak tanımlar.[^5] ITU-R SM.2060, farklı gerçek azimutlarda test düzeni,
ölçüm toplama ve hata değerlendirme adımlarını tanımlar.[^6] ITU-R SM.2097 ise
nihai kurulum ortamındaki yansıma, engel, girişim, sinyal seviyesi, modülasyon,
polarizasyon, yayın süresi ve bütünleşme süresinin ayrıca ölçülmesi gerektiğini
vurgular.[^7]

Rapor yalnız RMSE vermemelidir. Örnek sayısı, frekans, anten, polarizasyon,
mesafe, SNR/güç aralığı, açı adımı, ortalama hata (bias), medyan mutlak hata,
95. yüzdelik, maksimum hata, sonuç verilemeyen koşu sayısı ve ortam sınıfı da
kaydedilmelidir. Algoritmanın sonuç vermediği koşular RMSE paydasından sessizce
çıkarılamaz; `geçerli sonuç oranı` ayrı ölçülür.

## Başlıca fiziksel hata kaynakları

| Kaynak | Etki | Denetim |
|---|---|---|
| Açı referansı | Bütün kerterizlerde sabit bias | Gerçek kuzey referansı, ölçülü turntable/enkoder veya doğrulanmış pusula |
| Izgara adımı | Ham maksimumda kuantalama | 15° tam tarama; gerekirse tepe çevresinde daha ince ikinci tur |
| Anten ön/arka oranı | 180° belirsizlik | Karşı açı kapısı ve antenin frekans bazlı desen kaydı |
| Polarizasyon | Tepe yönünü ve seviyeyi bozabilir | TX/RX polarizasyonunu kayıt altına alma ve çapraz polarizasyon testleri |
| Çok yollu yayılım | Gerçek yol yerine yansıma tepesi | Açık görüş/temiz alan temel testi ve ayrı gerçek ortam testi |
| Yayın seviye değişimi | Sıralı açılarda sahte güç farkı | Eşit dwell, çoklu kare, ters yönde ikinci tarama ve kararlılık ölçüsü |
| Alıcı kazanç değişimi | Açı karşılaştırmasını geçersiz kılar | Aynı oturumda kazanç/ölçek kilidi |
| Komşu yayın | Geniş bant güç ölçümünü ele geçirir | Yalnız tespit edilen kanalın doğrusal gücünü bütünleştirme |
| Düşük SNR/kırpılma | Tepeyi oynatır veya düzleştirir | Tespit sürekliliği, SNR, doyum ve tepe belirginliği kapıları |

Şehir ve NLOS ortamlarında yayıcı anten deseni ile çok yollu yayılımın kerteriz
hatasını önemli ölçüde değiştirebildiği ayrıca gösterilmiştir.[^8] Bu nedenle
sayısal fixture veya kablolu güç deneyi saha RMS sonucuna dönüştürülemez.

## Ürün görev paylaşımı

| Katman | Nihai görev |
|---|---|
| FPGA / PL | Mevcut Hann → FFT → doğrusal güç → OS-CFAR zinciriyle hedefin varlığını ve spektral hücrelerini üretmek |
| ZedBoard ARM / PS | Aynı confirmed hedef ve sabit alıcı bağı için kanal gücünü birden fazla karede toplamak; ölçüm oturumunu, kalite kapılarını, ham maksimumu ve dairesel hata/RMS kayıtlarını yürütmek |
| Bilgisayar | HackRF USB alımı, operatörün gerçek anten açısı girişi, görev akışı, polar grafik/harita ve kanıt dosyasını sunmak |

Güncel ürün bu nihai dağılıma kısmen ulaşmıştır. FPGA/ARM tespit sonucu hedef
seçimini doğrular; geniş bant ortalama kaldırılmış ve yalnız seçili kanalın
doğrusal FFT gücü toplanır. Alan profili, ham maksimum, kalite kapıları ve
dairesel RMS taşınabilir C'ye aktarılmış; Python referansıyla sıfır fark ve
gerçek ZedBoard ARM ağ protokolü koşusu geçmiştir. Canlı arayüz 24 açı sonunda
sonucu `P0DF-v1` ile ARM'a doğrulatır. Açı başına kanal gücü bugün PC görüntü
FFT'sinden gelir; çoklu-kare PL/ARM kanal gücü bağı tamamlanmadan bu akış saha
sonucu yayımlamaya hazır değildir.

## Saha öncesi kabul sırası

1. **Sayısal model:** 0°–359° gerçek yönlerin her biri, 45°/30°/15° ızgara,
   0/360 sarımı, düz desen, çift tepe, ön/arka belirsizlik, ayar değişimi ve
   aynı-kare tekrarı sınanır.
2. **Portable C/ARM eşdeğerliği:** Aynı açı–güç kayıtları Python ve ARM C
   çekirdeğinde aynı ham maksimum, durum ve tolerans içinde aynı ara metrikleri
   üretir.
3. **Kart entegrasyonu:** Seçili hedefin FPGA tarafından doğrulandığı karelerden
   ARM kanal gücü alınır. CRC, olay kimliği, frekans, FFT boyutu, LNA/VGA ve
   örnekleme bağı değişirse oturum kapanır.
4. **Kablolu seviye deneyi:** RF yönü oluşturmadan farklı bilinen giriş
   seviyelerinde güç sıralaması ve kazanç kilidi ölçülür. Bu yalnız ölçüm zinciri
   testidir.
5. **Temiz fiziksel yön deneyi:** Bilinen azimutlu izinli kaynak, ölçülü anten
   açısı ve sabit geometriyle farklı frekans/polarizasyon/seviyelerde kör koşular
   yapılır.
6. **Gerçek ortam deneyi:** Yansıma ve engellerin bulunduğu yarışmaya benzer
   ortamda aynı profil değiştirilmeden RMSE, bias, p95, maksimum hata ve geçerli
   sonuç oranı raporlanır.

## Süre ve donanım sınırı

Masaüstü bilimsel referans, portable C/ARM çekirdeği, protokol, PetaLinux paket
tarifi ve geçici fiziksel kart sayısal kabulü tamamlandı. Kalan yazılım işi,
açı başına çoklu-kare PL kanal gücü ölçümünü ürün akışına bağlamak ve yeni imajın
kalıcı açılışını doğrulamaktır; donanım sorunu çıkmazsa yaklaşık bir yoğun çalışma
günü ölçeğindedir. Uygun yönlü anten, ölçülü açı referansı ve izinli bilinen
kaynak hazırsa fiziksel RMS veri toplama ve ilk hata analizi için en az bir tam
saha/laboratuvar günü gerekir. Ortam veya anten deseni sorunları çıkarsa
kalibrasyon ve ikinci kör tur ek süre gerektirir.

## Kaynaklar

[^1]: KrakenRF, [Kraken SDR DoA DSP, kaynak sürümü `2e1c4e6`](https://github.com/krakenrf/krakensdr_doa/tree/2e1c4e6a918f649f62c1b7a5c4c98a8b1bdc7e59), erişim 11 Eylül 2026.
[^2]: KrakenRF, [Direction Finding Quickstart Guide](https://github.com/krakenrf/krakensdr_docs/wiki/02.-Direction-Finding-Quickstart-Guide), güncelleme 28 Mart 2025.
[^3]: M. F. Iqbal, “Accuracy improvement in amplitude comparison-based passive direction finding systems by adaptive squint selection,” [IET Radar, Sonar & Navigation, 2020](https://doi.org/10.1049/iet-rsn.2019.0465).
[^4]: S. Karadağ, [Experimental Performance Evaluation of Direction Finding by Amplitude Comparison for GSM Applications](https://open.metu.edu.tr/handle/11511/23995), Orta Doğu Teknik Üniversitesi, 2014.
[^5]: ITU-R, [Report SM.2125-1 — Parameters of and measurement procedures on H/V/UHF monitoring receivers and stations](https://www.itu.int/dms_pub/itu-r/opb/rep/R-REP-SM.2125-1-2011-PDF-E.pdf), 2011.
[^6]: ITU-R, [Recommendation SM.2060-0 — Test procedure for measuring direction finder accuracy](https://www.itu.int/dms_pubrec/itu-r/rec/sm/R-REC-SM.2060-0-201411-I%21%21PDF-E.pdf), 2014.
[^7]: ITU-R, [Recommendation SM.2097-0 — On-site accuracy measurements of a fixed DF system](https://www.itu.int/dms_pubrec/itu-r/rec/sm/R-REC-SM.2097-0-201608-I%21%21PDF-E.pdf), 2016.
[^8]: C. Ziółkowski ve J. M. Kelner, [Radio bearing of sources with directional antennas in urban environment](https://arxiv.org/abs/1803.07011), 2018.
