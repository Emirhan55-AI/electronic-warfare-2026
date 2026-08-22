# Genlik Tabanlı Yön Bulma

Bu not `reference/p0/df.py` içindeki manuel, non-coherent P0 yöntemini ve
`reference/p0/df_fixtures.py` eğitim verisini açıklar. MUSIC, faz farkı veya
tek I/Q dosyasından yön çıkarımı yapılmaz.

## Fiziksel fikir

Yönlü anten kazancı açıya bağlıdır: `G(θ)`. Anten döndürüldüğünde aynı kaynağın
alınan gücü de değişir:

`P_r(θ) ∝ G(θ)`

Her açıdaki bounded IQ ölçümünde lineer ortalama güç

`P(θ_i) = (1/N) Σ |z_i[n]|²`

olarak hesaplanır; UI'ya kalibre edilmemiş göreli dBFS olarak verilebilir:

`P_dBFS = 10 log10(P/P_FS)`

Mevcut `ManualAmplitudeDF`, aynı açıdaki tekrarları güven ağırlıklı ortalar ve

`θ_hat = argmax_θ P(θ)`

ile en güçlü ölçülen açıyı seçer. En büyük ve ikinci büyük değer arasındaki
kontrast, açı kapsamı ve operatör güveni kalite metriğine katılır.

## Neden çok ölçüm gerekir?

Tek açı yalnız o yöndeki gücü söyler. Anten beamwidth'i geniş olabilir;
multipath farklı açılarda tepe oluşturabilir; gürültü ve kazanç değişimi ölçümü
oynatır. Ön/arka loblar 180° belirsizlik yaratabilir. Bu nedenle bütün çevrede
düzenli açılar ve mümkünse her açıda birden fazla ortalama gerekir. Bu yöntem
anten fazını kullanmadığı için MUSIC veya phase-coherent DF ile aynı değildir.

## Bağımsız sentetik eğitim fixture'ı

Fixture üreticisi estimatorü çağırmaz. 15° aralıklı 24 ölçüm için ileri lob,
zayıf arka lob ve küçük deterministik değişim üretir. UI'daki
`HOST/SYNTHETIC Eğitim Verisini Yükle` düğmesi gizli gerçeği `75°` olan sahneyi
yükler ve açıkça fiziksel test olmadığını yazar.

Çalışılmış örneğin seçilmiş açıları:

| Açı | Güç (yaklaşık dBFS) |
|---:|---:|
| 0° | -37,8 |
| 15° | -36,2 |
| 30° | -31,9 |
| 45° | -24,1 |
| 60° | -16,0 |
| 75° | -13,0 |
| 90° | -16,5 |
| 105° | -23,8 |
| 120° | -31,6 |

En büyük güç `75°` satırındadır; elle `argmax` sonucu `75°`, estimator sonucu
`75°`, dairesel hata `0°` olur. Ayrı kabul sahneleri `210°` ve wrap kontrolü
için `355°` gerçeğini de kullanır. `355° → 0°` sonucunun hatası
`min(|355-0|, 360-|355-0|)=5°` olarak hesaplanır.

## Terminal ve UI yürüyüşü

| Alan | İçerik |
|---|---|
| INPUT | Açı, aynı kanalda ortalanmış göreli güç, frekans ve ölçüm güveni |
| PROCESS | Aynı açıları birleştir → güç sırasına koy → argmax → kontrast/kalite |
| EQUATION | `P(θ)=1/N Σ|z[n]|²`, `θ_hat=argmax P(θ)` |
| OUTPUT | Açı–güç eğrisi, tahmini yön, güven ve LOB durumu |
| UI'da bakılacak | `HOST/SYNTHETIC veya REPLAY TEST`, yeterli açı, belirgin maksimum |

Uygulamada `YÖN BULMA` sekmesine gidip eğitim düğmesine basılabilir. Saha
akışında `ANTEN AÇISI (MANUEL)` fiziksel olarak elle konumlanan antenin operatör
girdisidir. Sıfır referansı açıkça `KUZEY / 0° COĞRAFİ` veya `MANUEL COĞRAFİ
BAŞ` seçilmedikçe bu açı coğrafi bearing'e dönüştürülmez. Pusula, IMU, enkoder
veya tahmini baş bilgisi yoktur. `GÜÇ ÖLÇ` yalnız seçili IQ kaynağından gelen
işlenmiş bounded karedeki ortalama lineer gücü kullanır; kaynak yoksa kayıt
oluşturmaz. Elle girilen değerler `MANUEL GİRİŞ` etiketiyle ayrı tutulur.

## Daha sonraki fiziksel deney

Fiziksel PASS ancak şu kontrollü deneyden sonra verilebilir:

1. Bilinen konum/yönde izinli kaynak kurulur.
2. Alıcı ve yönlü anten sabit noktaya yerleştirilir.
3. Kanal ve angular step seçilir; motor zorunlu değildir.
4. Anten elle her açıya döndürülür.
5. HackRF/alıcıdan bounded IQ alınır ve ortalama `|z|²` hesaplanır.
6. `θ/P` çifti kaydedilir ve bütün açıların grafiği çizilir.
7. Maksimum yön ile bilinen gerçek bearing karşılaştırılır.
8. Dairesel açı hatası ve çevresel koşullar raporlanır.

Sentetik fixture yalnız algoritma eğitimi ve UI binding kabulüdür; anten paterni,
multipath performansı veya fiziksel DF doğruluğu kanıtı değildir.
