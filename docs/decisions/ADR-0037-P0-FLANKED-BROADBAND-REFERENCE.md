# ADR-0037 — P0 İki Taraflı Geniş Bant Referansı

- Durum: Yazılım referansı ve bit-doğru RTL zinciri tamamlandı; güncel sentez,
  bitstream, kart ve kontrollü RF kabulü açık.
- Kapsam: KTR-4.1 sinyal tespiti, 2 MS/s × 4.096 hücreli P0 tespit karesi
- Ön koşullar: ADR-0028, ADR-0030, ADR-0033

## Sorun

Mevcut 16×256 bölgesel median ve 32-bin bütünleşik enerji yolu 100–256 bin
destekleri kurtarır. Yayın bir veya daha çok 256-bin bölgenin yarısından
fazlasını doldurduğunda aynı bölgenin medianı da yükselir. Bu durumda eşik
yayınla birlikte büyür ve 512–2048 bin genişlikteki kararlı destek kaçabilir.
Tek bir 4.096 hücreli pencerenin tamamını dolduran gürültü benzeri yayın için
aynı karede bağımsız yerel gürültü referansı yoktur; bu karar o durumu çözmüş
sayılmaz.

## Karar

Rank-24/32 OS-CFAR ve 41–256 bin bölgesel kurtarma değiştirilmez. Bunlara,
yalnız 257 bin ve daha geniş destekler için ayrı bir yol eklenir:

1. Mevcut on altı bölgesel çift-median küçükten büyüğe seçilir; dördüncü
   bölge medianı kaba çerçeve referansıdır.
2. Aynı 32-bin kayan toplam bu referansın Q48 `2,5` enerji eşiğini aşan
   hücrelerde kaba destek üretir.
3. Destek en az 257 bin olmalı ve iki yanında, desteğin bulunduğu bölgelerin
   bir ötesinde birer tam referans bölgesi bulunmalıdır.
4. Desteğe değen bölgelerdeki en yüksek median, iki dış referansın yüksek
   medianını `2,5` kat aşmalıdır. Bir tarafı olmayan kenar desteği bu yolda
   aday olmaz.
5. Geçerli geniş adayla çakışan bölgesel ve OS-CFAR parçaları bastırılır;
   diğer adaylar korunur ve çıktı frekans sırasında kalır.

Dördüncü sıra ve `2,5` katsayısı şartname değeri değildir. Alt-kantil,
kirlenmiş referansların çoğunlukta olmadığı durumda gürültü adayını korur;
iki dış bölge kontrolü eğimli veya basamaklı gürültünün tek başına geniş yayın
sayılmasını engeller. Bu özel bileşimin saha yanlış alarm olasılığı kapalı
formda `10⁻⁴` değildir; ölçülmesi gerekir.

## Doğrulanan kapsam

- Bağımsız 64'er sentetik CI8/Hann karesinde 512, 1024 ve 2048 bin destekler
  64/64 kurtarılmış; düz, 12 dB eğimli ve 12 dB basamaklı gürültü ailelerinde
  0/64 geniş aday görülmüştür.
- Konum/SNR tanısında 10 kat güç oranında 384–2048 bin genişliklerin 672/672
  karesi en az `%80` kapsamayla kurtarılmıştır. 5 kat oranında sonuçlar
  636/672'dir; bu seviye kazanılmış saha eşiği değildir.
- Sabit noktalı referans ile SystemVerilog, 512 ve 2048 bin pozitifleri ve
  12 dB basamak negatifini içeren sekiz karede 24 geniş bant adayı / 27 AXI
  kaydı için sıfır metadata farkı vermiştir. Alt-aşama en kötü gecikmesi
  44.886 çevrimdir.
- Birleşik azaltıcı sekiz karede 63 nihai aday / 65 kayıt, paket sınırı 379
  AXI64 beat üretmiştir. En kötü azaltıcı gecikmesi 45.557 çevrim; girişle
  birlikte işlevsel kapasite 1006,99 kare/s'dir.

Bu sonuçlar sentez, yerleştirme, zamanlama, bitstream veya kart ölçümü değildir.
Güncel RTL kartta doğrulanmadan eski fiziksel 2 MS/s kanıtı yeni algoritmaya
aktarılmaz.

31 Ağustos 2026 kayıtlı RF tekrarında, 1.300 MHz çıkış merkezindeki aynı güçlü
destek iki farklı fiziksel LO ile kaydedilmiştir. Mevcut karta CI8 tekrarında
merkezi ±50 kHz kapsayan kararlı destek iki kayıtta da 0/120 iken, bu kararın
periyodik Hann yazılım referansı aynı veride 120/120 + 120/120 destek üretmiştir.
1.310 MHz karşılaştırma kaydında bu merkezi destek 0/120'dir. Kaynak kimliği
beyan edilmemiştir; yöntem karşılaştırması RF yayıncı kimliği veya saha Pfa
ölçümü değildir. Ham veri, SHA-256 bağları ve iki tekrar raporu
`build/acceptance/rx-survey/diagnostic-08d7f4d1bbe342fdb98c5deefba2b902/`
içindedir. Kartta çalışan yöntem ile yazılım arasındaki bu fark, ayrı yeni
bitstream/kart kabulünü zorunlu kılar; mevcut fiziksel kabul genişletilmez.

## Açık sınırlar

- Bütün 2 MHz pencereyi dolduran yayın bağımsız referanssızdır.
- Pencere kenarı için ürün taraması 600 kHz sorumluluk adımlı örtüşen 2 MHz
  ayarlara geçirilmiş, 1 MHz desteğin bir ayarın ±800 kHz geçiş bandında kalması
  geometrik testle doğrulanmıştır. Geniş aday ikinci ayarda tepe yerine mutlak
  destek örtüşmesiyle eşleştirilir. Bu host tarama çözümü kart/RF kabulü değildir.
- Kontrollü RF'de algılama olasılığı, yanlış doğrulanmış olay/dakika, ilk
  tespit gecikmesi ve kazanç/frekans zarfı ölçülmemiştir.
- Güncel sentez/route ve kart hizmet hızı yeniden çalıştırılmalıdır.

## Bilimsel bağ

Karar, kirlenmiş referanslara dayanıklı order-statistic/censored gürültü
kestirimi ile clutter-edge durumunda ayrı iki taraflı referans kullanma
ilkelerine dayanır. FCME çalışmaları gürültü tabanı hatasının algılama ve
yanlış alarmı doğrudan etkilediğini; güvenilir gürültü örneklerinin sinyal
örneklerinden ayrılması gerektiğini gösterir. Bu kaynaklar buradaki dördüncü
bölge sırasını veya `2,5` katsayısını tek başına belirlemez; sayısal seçimler
yukarıdaki bağımsız deney ve donanım eşdeğerliği kapılarına bağlıdır.

- Rohling, *Radar CFAR Thresholding in Clutter and Multiple Target
  Situations*, IEEE Transactions on Aerospace and Electronic Systems, 1983.
- Iwata ve diğerleri, *A Study on the False Alarm Probability of the FCME
  Algorithm*, IEEE Access, 2021, DOI: 10.1109/ACCESS.2021.3070549.
