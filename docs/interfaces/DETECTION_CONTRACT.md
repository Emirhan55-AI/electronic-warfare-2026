# PHASE-03 Tespit Sözleşmesi

## Girdi ve indis düzeni

Detector girdisi PHASE-02 Hann/4096 FFT zincirinin `fftshift` sıralı, sonlu ve negatif olmayan lineer `bin_power_fs2` dizisidir. Örnekleme hızı metadata'dan gelir. İlk ve son 20 hücre değerlendirilmez. Merkez politikası `değerlendir` için 4.056, `dışla` için 4.055 CUT kullanır; merkez dışarıdaysa yanlış alarm paydasına katılmaz.

Sentetik katalog ve ground truth indisleri shifted düzendedir. Frekans alanında oluşturulan geniş bant/eğimli/basamaklı katsayı dizisine önce `numpy.fft.ifftshift()`, ardından `numpy.fft.ifft()` uygulanır. Üretilen I/Q gerçek PHASE-02 Hann/FFT/`fftshift` zincirinden geçer ve test enerji konumunun beklenen shifted hücrelere döndüğünü doğrular.

## Doğrulanmış parametre zarfı

`Pfa/CUT` değerleri `1e-3`, `1e-4`, `1e-5`; merkez politikası `değerlendir` veya `dışla` olabilir. Bölgesel yöntem için çarpan `-ln(Pfa)`, CA-CFAR için `32(Pfa^(-1/32)-1)`, OS-CFAR için 32 eğitim hücresinin 24. sırasına ait gamma-oran denkleminin deterministik köküdür. Varsayılan seçim `1e-4` ve merkez `değerlendir` üzerinden yapılır. Ayar değişimi pipeline neslini ve temporal durumu sıfırlar.

## Aday yöntemler ve tarafsız seçim

Bölgesel sağlam taban, CA-CFAR ve OS-CFAR başlangıçta eşit adaydır. Zorunlu yanlış alarm, dar/çoklu/geniş bant, merkez/kenar, temporal ve bounded çalışma kapılarından biri geçilmezse yöntem elenir. Birden çok yöntem geçerse en az 0,02 dengeli puan farkı ve sıfırın üzerinde eşlenik bootstrap alt sınırı anlamlı üstünlüktür; aksi durumda ölçülebilir kaynak maliyeti anahtarı kullanılır. Birleşik yöntem yalnız tekil yöntemlerin geniş bant kusurunu en az 0,10 giderirse ve diğer kapıları bozmazsa değerlendirilir. Hiçbiri geçmezse profil kurulmaz.

Maliyet anahtarı sırasıyla frame başına seçim girdisi sayısı, kalıcı durum slotu, en geniş seçim grubu ve temel aritmetik işlem sayısıdır; Big-O ifadesi içermez ve yalnız istatistiksel eşitlikte kullanılır.

## Ölçümler

Dar bant başarısı, katalogdaki ana-lob desteğiyle kesişen ve beklenen tepe toleransını sağlayan doğru bölgeyi gerektirir; diğer bölgeler yanlış adaydır. Çoklu sinyal başarısı iki ayrı bölge, birleşmeme ve zayıf hedefin maskelenmemesini birlikte gerektirir. Geniş bant başarısı tek-frame gruplanmış kaba bölgede en az `0,60` kapsama, `0,50` IoU ve en fazla `0,25` gereksiz taşmayı birlikte gerektirir. Tek hücre kesişimi başarı değildir ve kaba bölge kesin bant genişliği sayılmaz.

Temporal katman 2/3 doğrulama ve iki ardışık kaçırmada sonlandırma kullanır. Aktif track 64, sona ermiş geçmiş 128, UI görünümü 12 ile sınırlıdır. Taşmada mevcut track'ler korunur, en güçlü/yakın yeni adaylar deterministik sırayla alınır; geçmişte en eski biten olay çıkarılır ve kayıp sayısı UI'da gösterilir. Split/merge, tam çoklu hedef takibi değildir: eşleşme önce bin mesafesi, sonra event kimliği ve bölge sırasıyla greedy yapılır; eşleşmeyen parça yeni track olur.

## İstatistik sözleşmesi

Her gürültü seviyesi, Pfa ve merkez politikası için 1.024 bağımsız frame; eğimli/basamaklı gürültü için 512 frame; her dar bant SNR noktası ve detector için 256 eşlenik frame; çoklu ve geniş bant sahneleri için 256 frame; merkez/kenar için 128 frame; her temporal aile için 128 bağımsız dizi kullanılır. Seed türetimi katalogda sabittir. Frame/dizi düzeyinde 10.000 tekrarlı percentile bootstrap kullanılır. Yöntemler aynı scene/frame/dizi kimliğini paylaşır; bootstrap dört katmanı ayrı eşlenik örnekler ve eşit ağırlıklı ortalamasını alır.

Bu çıktı kayıtlı/sentetik I/Q üzerinde referans tespittir. dBm, yayın türü, kesin bant genişliği, canlı RF, HackRF gerçek zaman veya FPGA yeteneği iddiası değildir.
