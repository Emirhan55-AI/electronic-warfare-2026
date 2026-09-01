# ADR-0038 — PHASE-08 Geniş Host Kaba Tespiti

- Durum: Host referansı ve ürün bağı kabul edildi; RF/FPGA doğrulama açık
- Kapsam: 8 MS/s HackRF önizlemesinden kaba RX adayı üretimi
- Bağlı gereksinimler: KTR-4.1, KTR-4.1-OPS-B0
- Ön koşullar: ADR-0036, ADR-0037

## Bağlam

Ürün tek HackRF sürecinden 8 MS/s, 16.384 kompleks örnek alır. Aynı veri 8 MHz
spektrum/waterfall için hostta işlenirken, doğrulanmış ayrıntılı tespit yolu
kanal seçiciden sonra 2 MS/s, 4.096 örnek olarak ZedBoard'a gider. 2 MHz karar
penceresinin tamamını dolduran gürültü-benzeri yayın, aynı pencerede bağımsız
gürültü referansı bırakmadığı için OS-CFAR ve bölgesel medianla koşulsuz
ayrılamaz.

Enerji tespiti bilinmeyen dalga biçimleri için yerleşik bir yaklaşımdır; ancak
gürültü gücü belirsizliği düşük SNR'de sağlamlık sınırı oluşturur. Bu nedenle
tek dolu pencerenin seviyesini eşik düşürerek sinyal ilan etmek kabul edilmez.
[Urkowitz, 1967](https://doi.org/10.1109/PROC.1967.5573) ve
[Tandra–Sahai, 2008](https://doi.org/10.1109/JSTSP.2007.914879).

## Karar

8 MHz görüntü FFT'sinin kaydırılmış lineer güç hücreleri dörderli toplanır.
Enerji korunarak 16.384 hücreden 4.096 hücreye inen bu spektrum mevcut
rank-24/32 OS-CFAR ve ADR-0037 geniş bant çekirdeğine verilir. Host OS-CFAR
hesabı, kanonik Python sonucuyla aday alanlarında birebir eşdeğer vektörize
uygulamadır. Kullanılabilir kaba alan alıcı merkezinin ±3 MHz çevresidir;
±100 kHz DC alanına yalnız dar aday denk gelirse elenir. Merkez veya örnekleme
bağı değiştiğinde 2/3 geçmişi sıfırlanır.

Bu aşama **hostta Python/NumPy ile çalışır** ve yalnız `kaba RX adayı` üretir.
SystemVerilog ile çalışan 2 MHz Hann/FFT/güç/OS-CFAR/geniş bant zincirinin
yerini almaz. Arayüz kaba adayı sarı kesik alanla, zamansal FPGA adayını düz sarı
alanla ayrı gösterir. RX-only modunda FPGA sonucu üretildiği izlenimi verilmez.

FFT öncesi Hann penceresi ve kısa değiştirilmiş periodogram yaklaşımı spektral
sızıntıyı yönetir; daha kararlı güç kestirimi için zaman ortalamasının
çözünürlük/tepki süresi karşılığı ayrıca ölçülmelidir.
[Welch, 1967](https://doi.org/10.1109/TAU.1967.1161901).
OS-CFAR'ın çoklu hedef ve değişen arka plan gerekçesi
[Rohling, 1983](https://doi.org/10.1109/TAES.1983.309350) ile uyumludur; makale
bizim hücre sayılarımızı veya saha Pfa değerimizi belirlemez.

## Host kabulü

Ürün kodundan bağımsız tohumlarla her ailede 32 sentetik CI8/Hann karesi
çalıştırılmıştır. 100 kHz, 500 kHz, 1 MHz, 2 MHz ve 4 MHz ailelerinde `%80`
destek kapsaması 32/32; düz, 12 dB eğimli ve 12 dB basamaklı gürültüde kaba
aday 0/32 olmuştur. 6 MHz aile 31/32 olduğundan kabul zarfına alınmamış,
yalnız karakterize edilmiştir. Tüm 8 MHz'i dolduran aile 0/32 adayla bilinen
sınırı yeniden üretmiştir.

Vektörize detector çağrısı 320 örnekte p50 `4,29 ms`, p95 `5,86 ms`, azami
`26,63 ms` ölçülmüştür. Bu süre FFT, USB, Qt çizimi ve frekans ayar süresini
içermez. Kaynak bağlı sonuç
`results/evidence/phase08/coarse-rx-detection-v1.json` dosyasındadır.

## Açık kapılar

- Kaba adayın 2 MHz FPGA yeniden ayarıyla otomatik doğrulama ve tarama süresi.
- Güncel ADR-0037 bitstream'i, kart kabulü ve Ethernet köprüsünün yetkili açılışı.
- Kontrollü RF negatif/pozitifleriyle Pd, yanlış olay/dakika ve ilk tespit gecikmesi.
- 4 MHz üzeri destekler ve bütün 8 MHz doluluğu için komşu ayar veya ölçülmüş
  frekans/kazanç tabanı. Güvenilir referans yoksa sonuç `belirsiz` kalır.
