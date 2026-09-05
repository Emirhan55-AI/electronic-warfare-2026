# ADR-0041 — PHASE-08 Hiyerarşik Kör Sinyal Tespiti

- Durum: ST-04 mimari seçimi tamamlandı; ürün kabulü açık
- Kapsam: 20 MHz–6 GHz bilinmeyen frekans araması ve ayrıntılı doğrulama
- Bağlı gereksinimler: KTR-4.1, KTR-4.1-OPS-B0
- Ön koşullar: ADR-0037, ADR-0038, ADR-0039, ADR-0040

## Bağlam

Mevcut 2 MS/s, 4.096-hücre FPGA/ARM yolu ayrıntılı karar verir fakat 20 MHz–6
GHz aralığında 600 kHz sorumluluklu pencereler ve pencere başına 128 kare ile
yalnız ham örnek toplama alt sınırı yaklaşık 43,55 dakikadır. Bu yol tam bant
ilk keşif için kullanıldığında kısa ve aralıklı yayınların yeniden ziyaret
süresini karşılamaz.

Resmî `hackrf_sweep` ile 20 MHz–6 GHz aralığı 1 MHz, 100 kHz ve 25 kHz istenen
güç hücrelerinde üç bağımsız süreçte üçer kez ölçülmüştür. 27/27 tur boşluksuz,
USB shortfall sayacı sıfırdır. Üç profilin süreç medyanları %3,80 içinde kalmış,
25 kHz profilinin medyanı 0,794019 ve p95 değeri 0,804672 saniye olmuştur. En
ince profil tur başına yaklaşık 2,00 MB ham CSV üretir.

Aynı fiziksel 955,7 MHz açık/kapalı CI8 öneğinde 4.096 ve 8.192 FFT hedefi
kaçırmış; 16.384 FFT hedefi iki LO'da geri kazanıp kapalı kayıtta ortak aday
üretmemiş; 32.768 ve 65.536 FFT kapalı kayıttaki sabit çizgileri de ortak aday
yapmıştır. Bu kayıt kör kabul değildir ve ürün profili seçmeye yetmez.

## Karar

Kontrollü kör RF deneyi üç aşamalı aday mimarisiyle yapılacaktır:

1. Host, 20 MS/s resmî `hackrf_sweep` ve istenen 25 kHz hücreyle 20 MHz–6 GHz
   aralığını tarar. Bu aşama yalnız kaba aday üretir.
2. Host, aday çevresini 8 MS/s, periyodik Hann ve 16.384 FFT ile bütünleştirir;
   aynı mutlak RF frekansını ikinci LO'da arar. Sonuç yalnız RX kanıtıdır.
3. Mevcut FPGA PL 2 MS/s, 4.096 FFT, OS-CFAR ve çok ölçekli yolu çalıştırır;
   ARM zamansal durumu yönetir. FPGA/ARM dışında onay gösterilmez.

25 kHz Stage-0 ve 16.384 Stage-1 değerleri yalnız kontrollü kör deney için
kilitlenir. Farklı frekans, yayın ailesi, seviye ve sürelerden oluşan holdout
geçilmeden ürün profili sayılmaz ve eşikler değiştirilmez.

## FPGA sınırı

Mevcut 2 MS/s RTL'nin işlevsel kapasitesi 50 MHz'de yaklaşık 991,375 kare/s,
gereksinimi 488,281 kare/s'dir. Aynı 4.096-hücre zincirin doğrudan 8 MS/s
çalışması 1.953,125 kare/s ister; mevcut işlevsel kapasite bunun yaklaşık
%50,76'sıdır. Güncel tam tasarım 48.040/53.200 LUT (%90,30), 73/140 BRAM
(%52,14) ve 77/220 DSP (%35) kullanır; route 50 MHz'de setup WNS +0,199 ns ve
hold WHS +0,010 ns ile geçmiştir.

Bu kanıt başka bir 8 MS/s FPGA mimarisinin yapılamayacağını söylemez. Mevcut
RTL'yi doğrudan hızlandırmayı ve kanıtsız 16.384-hücre FPGA ekini seçmez. Kaba
arama hostta, ayrıntılı karar mevcut FPGA/ARM zincirinde kalır.

## Açık kapılar

- Stage-0 güçlerinden truth kullanmadan aday çıkarma ve Stage-1'e otomatik geçiş.
- Kontrollü iletim düzeninde farklı bant/yayın/seviye/süre kör matrisi.
- Pd, yanlış doğrulanmış olay/MHz-dakika ve p95 ilk tespit gecikmesi.
- Adaydan iki LO ve FPGA/ARM kararına uçtan uca yaşam döngüsü.

Kaynak bağlı karar kaydı
`results/evidence/phase08/st04-hierarchical-detection-architecture-v1.json`
dosyasındadır. Bu ADR ST-04 mimari seçim işini kapatır; ST-05–ST-08 ve
PHASE-08 ürün kabulünü kapatmaz.
