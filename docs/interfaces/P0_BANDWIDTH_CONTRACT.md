# P0 Zorunlu Bant Genişliği Sözleşmesi

## Tanım

Zorunlu çıktı `B_hat = f_H - f_L` biçimindedir. OS-CFAR adayı yalnız bounded
kaba ROI sağlar; `candidate.end_bin - candidate.start_bin` doğrudan zorunlu bant
çıktısı değildir ve UI'da `Kaba Aday Aralığı` adıyla ayrı gösterilir.

Estimator şu deterministik sırayı uygular:

1. 32 hücrenin 24. exponential order statistic değeri beklenen oran
   `E[X_(24)]/mean` ile yerel ortalama gürültüye çevrilir.
2. FFT gücü `[0.25, 0.50, 0.25]` çekirdeğiyle yumuşatılır.
3. Yerel ortalama gürültünün 6 dB üstündeki hücreler, en fazla iki-bin boşluk
   köprülenerek aday peak'ine bağlı threshold desteğini oluşturur.
4. Threshold desteği parçalıysa, arama sınırına taşıyorsa veya %98 occupied-power
   genişliğinin 1,15 katını aşıyorsa sonuç kararsız sayılır.
5. Kararsız durumda yalnız kaba ROI içinde yerel gürültü çıkarılmış toplam
   excess gücün ortadaki %98'ini taşıyan sınırlar açıkça
   `occupied_power_fallback` olarak kullanılır.

Sonuç nesnesi threshold, occupied-power, kaba ROI ve seçilmiş kanonik sınırları
ayrı taşır. UI `Bant Genişliği`, `Alt Sinyal Sınırı`, `Üst Sinyal Sınırı`,
`Bant Ölçüm Yöntemi` ve `Kaba Aday Aralığı` alanlarını ayrı gösterir.

## Kabul sınırı

Golden sahneler 4096 FFT ve 1.024 MS/s ile 250 Hz/bin çözünürlüktedir. Tek ton,
AM, NFM, OOK-benzeri sayısal burst, 21-bin dikdörtgen spektrum, 81-bin bant
sınırlı gürültü, iki komşu emitter ve eşik yakını zayıf ton ölçülür. Toleranslar
fixture fiziği ve gerçek FFT bin çözünürlüğüyle 1,2–5 bin arasında açıkça
kaydedilir; sub-bin bant hassasiyeti iddia edilmez.

Bu sözleşme host/sentetik kanıttır. Kalibre RF, PS/ARM veya ZedBoard çalışması
değildir.
