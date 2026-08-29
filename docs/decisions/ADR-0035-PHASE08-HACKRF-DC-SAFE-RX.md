# ADR-0035 — PHASE-08 HackRF DC-Güvenli Canlı RX

- Durum: Kabul edildi
- Kapsam: HackRF-1 canlı RX ve host ED arama yolu
- Bağlı gereksinimler: KTR-4.1, KTR-4.1-OPS, KTR-6
- Ön koşullar: PHASE-08A, ADR-0034

## Bağlam

İlk fiziksel HackRF gözleminde cihaz ve bounded `ci8` aktarımı başarılı olmuş,
ancak dar hakem bandını tam merkezden tune eden yol HackRF One zero-IF DC
çıkıntısını gerçek aday gibi doğrulamıştır. Great Scott Gadgets HackRF
dokümantasyonu, merkez FFT çıkıntısının alıcı ölçüm artefaktı olduğunu ve temel
çözüm olarak offset tuning kullanılmasını önerir.

Merkezden kaçık geçici ölçümde 104,4–104,9 MHz gözlem aralığındaki geniş bant
yapı beş koşunun tamamında yeniden görülmüştür. Böylece merkez artefaktı ile
canlı RF yapısı birbirinden ayrılmıştır.

## Karar

HackRF tuning profili merkez çevresindeki ±100 kHz aralığı tespit adaylarından
çıkarır. Her istenen aralık, en çok 2,5 MHz'lik bitişik alt aralıklara bölünür;
her alt aralık 500 kHz offset ile tune edilir. İstenen alt aralık fiziksel
alıcı merkezini içermez ve 6 MHz kullanılabilir analiz bandının içinde kalır.
Komşu alt aralıklar uç uca bitişir; başka bir pencerenin DC çentiğine düşen
frekans önceki pencerede kapsanır.

Bounded capture içinde herhangi bir karede 2-of-3 ile doğrulanmış son geçerli
gözlem, capture sonu iki boş kareyle bitse dahi arama sonucu olarak korunur.
Bu davranış bir sinyalin tarama sırasında görülmesini kaybetmez; capture'lar
arasında sınırsız veya gizli temporal durum taşımaz.

## Fiziksel kabul

Seri numarası `0000000000000000a32868dc35138247` olan tek `ED_RX` cihazı,
firmware `v2.4.0`, 8 MS/s, RF amplifier kapalı, LNA/VGA 16 dB ile kullanılmıştır.
104,4–104,9 MHz aralığı 103,9 MHz merkezden alınmıştır. Beş bağımsız koşunun
tamamında `LIVE_HACKRF` kaynaklı en az bir doğrulanmış aday oluşmuştur. Toplam
81.920 kompleks örneğin byte uzunlukları tamdır ve doyan bileşen sayısı sıfırdır.
Kanıt `results/evidence/p0/hackrf-rx-physical-acceptance.json` dosyasındadır.

## Sınır

Bu karar fiziksel HackRF bounded RX ve host tespitini kanıtlar. Görülen yayının
kimliğini, parametre doğruluğunu, dBm kalibrasyonunu, USB sürekli hızını,
ZedBoard/FPGA aktarımını, saha kapsamasını veya herhangi bir RF TX işlevini
kanıtlamaz.
