# ADR-0042 — PHASE-08 ST-05 Geniş Bant Tespit Referansı

- Durum: ST-05 Python referansı seçildi; ST-06 ürün ve donanım uygulaması açık
- Kapsam: 4.096 hücreli ayrıntılı doğrulamada geniş bant yayın önerisi
- Bağlı gereksinimler: KTR-4.1, KTR-4.1-OPS-B0

## Problem

Mevcut dar bant OS-CFAR zinciri, referans penceresini doldurmayan çizgisel ve dar
yayınlar için korunacaktır. Aynı yerel referans mantığı geniş bir yayının içine
girdiğinde referans hücreleri yayın gücüyle kirlenir. Tek bir alıcı penceresinin
tamamını dolduran gürültü benzeri yayın ise kalibrasyon, zaman referansı veya
başka bir LO gözlemi olmadan yalnız daha yüksek alıcı gürültüsünden ayırt
edilemez. Bu durumda `yayın yok` kararı üretmek gözlenenden daha güçlü bir
iddiadır.

İlk teşhiste mevcut bölgesel yöntem güçlü, merkezlenmiş 100–2.048 hücre
örneklerini bulmuş; 4.096 hücre örneklerinin 64/64'ünü kaçırmıştır. Basit global
medyan karşılaştırması 12 dB eğimli ve basamaklı gürültü ailelerinin her birinde
64/64 yanlış geniş bant aday üretmiştir. Bu nedenle yalnız global referans veya
eşik düşürme seçilmemiştir.

## Karar

Dar bant `P0_OS_CFAR_EXPONENTIAL_PFA_1E4` ve katsayısı değiştirilmez. ST-05
geniş bant Python referansı şu ayrı zinciri kullanır:

1. Sekiz güç karesi zaman boyunca ortalanır.
2. 32, 64, 128 ve 256 hücreli bütünleşik enerji ölçeklerinden herhangi birinde
   mevcut `2,5 ×` mühendislik eşiğini geçen tohum aranır.
3. Yayın desteği `1,5 ×` büyüme seviyesi ve sekiz hücreli ortalamayla çıkarılır;
   dört hücreye kadar boşluk tek desteğe birleştirilir.
4. En az 41 hücrelik destek için iki yanda bağımsız 64 hücreli referans gerekir.
   Referanslar arasında en fazla 3 dB fark kabul edilir.
5. Destek gücü sekiz karenin en az altısında iki referansın büyüğünün `2,5 ×`
   üstünde olmalıdır.
6. Referanslardan biri görünmüyorsa aday doğrulanmaz ve `retune_required`
   üretilir. Sonuç hiçbir durumda mutlak `yayın yok` iddiası taşımaz; yalnız
   gözlenen pencere içinde sınırları görülebilen aday bulunmadığını söyleyebilir.

Bu sayılar holdout çalıştırılmadan önce
`config/st05_wideband_evaluation.json` içinde dondurulmuştur. `2,5 ×` dar bant
Pfa katsayısı değildir; önceki geniş bant mühendislik profilinden korunan enerji
oranıdır. `1,5 ×`, 64 hücre ve 3 dB değerleri de kalibre edilmiş saha
olasılıkları değildir.

## Bilimsel dayanak ve sınır

Rohling'in OS-CFAR çalışması, sıralı istatistik referansının çoklu hedef ve
homojen olmayan arka plan koşullarındaki amacını açıklar; bu nedenle dar bant
OS-CFAR korunur: <https://doi.org/10.1109/TAES.1983.309350>.

Welch'in değiştirilmiş periodogramları zaman boyunca ortalama yaklaşımı, kareler
arası güç bütünleştirmesinin temelidir: <https://doi.org/10.1109/TAU.1967.1161901>.

Tandra ve Sahai, gürültü belirsizliğinin bilinmeyen sinyal enerji tespitinde
yalnız daha uzun gözlemle aşılamayan bir SNR duvarı oluşturabileceğini gösterir:
<https://doi.org/10.1109/JSTSP.2007.914879>. Tam pencere için mutlak yokluk
iddiasından kaçınma ve bağımsız referans/yeniden ayar isteme bu sınıra dayanır.

Seçilen yöntem bu makalelerin birebir algoritması değildir. Literatürdeki
referans kirliliği, periodogram ortalama ve gürültü belirsizliği ilkelerini
önceden dondurulmuş proje zarfına uygulayan bir mühendislik profilidir.

## Holdout sonucu

Bağımsız üstel güç hücresi modelindeki 15 sahne, sahne başına 64 dizi ve dizi
başına sekiz kareyle toplam 960 dizi değerlendirilmiştir. Seçilen referans:

- 256/256 merkezlenmiş geniş yayın dizisini sınır kapısıyla,
- 128/128 yakın/uzak güçlü-zayıf ayrım dizisini,
- 64/64 birleşmesi gereken yakın yayın dizisini,
- 192/192 gürültü dizisini sıfır geniş bant olayla,
- 128/128 kenar dizisini yeniden ayar isteğiyle,
- 64/64 geçici ve 64/64 kalıcı yayın dizisini beklenen zamansal sonuçla

geçmiştir. Tam pencere ailesinin 64/64'ünde mutlak yokluk iddiası üretilmemiştir.
Kaynak bağlı sonuç
`results/evidence/phase08/st05-wideband-holdout-v2.json` dosyasındadır. İlk v1
değerlendiricisindeki aynı adayın iki gerçek desteğe sayılabilmesi kusuru,
eşiklere ve sahnelere dokunmadan v2'de bire bir eşlemeyle düzeltilmiştir.

## FPGA/ARM etkisi

Mevcut yerleştirilmiş PL tasarımı 48.040/53.200 LUT (`%90,30`) kullandığı için
bu Python referansı ST-05'te RTL'e eklenmez. ST-06, aynı kararları sabit nokta
model, C/PS ve SystemVerilog/PL seçenekleri arasında kaynak ve hız ölçerek
paylaştıracaktır. En olası sınır; Hann, FFT, güç ve seyrek dar bant adayının
PL'de, çok kareli durum ve yeniden ayar kararının ARM'da kalmasıdır. Ancak bu
yerleşim ST-06 sentez ve eşdeğerlik kanıtından önce ürün mimarisi sayılmaz.

Bu ADR sentetik Python referans seçimini kapatır. Canlı RF, FPGA/ARM eşdeğerliği,
sentez/route, ürün bağlantısı, Pd/Pfa ve kör saha kabulü açık kalır.
