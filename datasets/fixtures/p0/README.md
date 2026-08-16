# P0 Deterministik ED Fixture Sözleşmesi

`reference/p0/fixtures.py` yedi sentetik ve sabit seed'li sahne üretir: tek ton,
AM-benzeri, NFM-benzeri, sayısal OOK burst, geniş bant gürültü-benzeri, iki komşu
sinyal ve eşik yakını zayıf ton. Veriler gerçek RF kaydı değildir.

Genel centroid toleransı 300 Hz'dir. Rastgele fakat seed-sabit geniş bant
spektrumun enjekte edilen exact güç centroid'i ground truth alınır ve pencereleme
etkisi için 1000 Hz tolerans kullanılır. Bant toleransları sırasıyla 300, 1000,
1250, 1000, 500 ve 300 Hz'dir. Eşik yakını sahnede bant truth tanımlı değildir;
yalnız strict tespit, centroid, göreli güç ve SNR raporlanır.

Geniş bant gürültü-benzeri sahnenin bölgesi fixture tarafından bilinir; bu sahne
OS-CFAR geniş bant tespit iddiası için değil, parametre/sınıflandırma abstention
kapısı için kullanılır. Diğer hedef bölgeler OS-CFAR çıktısından seçilir ve gerçek
2-of-3 temporal modelinden geçirilir.
