# ADR-0036 — PHASE-07 Kanal Seçici ve Ağ Köprüsü

- Durum: Kabul edildi; PHASE-07 uçtan uca fiziksel kapıları tamamlandı
- Kapsam: HackRF host çıkışı ile ZedBoard yerel ED hizmeti arasındaki veri yolu
- Bağlı gereksinimler: KTR-4.1, KTR-6
- Ön koşullar: ADR-0034, ADR-0035

## Bağlam

Fiziksel HackRF kabulü `8 MS/s` bounded RX üretirken ZedBoard'ın kalıcı ve
ölçülmüş gerçek zaman profili `2 MS/s`, `4.096` kompleks `ci8` örnektir. Ham
8 MS/s veriyi örnek atlayarak azaltmak alias üretir. Önceki ağ codec'i yalnız
payload CRC'si taşıyor, ürün FPGA profilini zorlamıyor ve kart tarafında gerçek
bir ağ köprüsü bulundurmuyordu.

Kartın mevcut ayrıcalıksız yerel hizmeti ve dört çerçevelik istek boruhattı
korunmalıdır. Ağ dinleyicisinin DMA erişimi kazanması veya genel ağ arayüzlerine
açılması gerekmemektedir.

## Karar

PC tarafında stateful sayısal kanal seçici kullanılır. İstenen çıkış merkezi
NCO ile temel banda taşınır; 193 tap Kaiser pencereli alçak geçiren FIR,
±800 kHz passband ve ±1 MHz stopband başlangıcıyla uygulanır; 4:1 polyphase
örnek azaltma `2 MS/s × 4.096` CI8 çerçeve üretir. Canlı profilde 1,5 MHz offset
tuning HackRF zero-IF bileşenini çıkış bandının dışında bırakır.

Ağ protokolü sürüm 2 olur. `P0IQ` isteği 48 bayt başlıkta hem metadata CRC32
hem payload CRC32 taşır ve FPGA yolunda tek chunk/2 MS/s/4.096/8.192 bayt
alanlarını fail-closed zorlar. `P0RS` yanıt zarfı sıra numarası, bounded uzunluk,
başlık CRC32 ve payload CRC32 taşır.

Linux ağ köprüsü tam IPv4 bind ve tam peer allowlist kullanır; tek istemci ve
dört istek derinliğiyle TCP backpressure uygular. Doğrulanmış çerçeveler mevcut
`AF_UNIX/SOCK_SEQPACKET` hizmete iletilir. Ağ köprüsü DMA'yı açmaz ve ilk ağ
karesinde temporal durumu sıfırlar.

## Donanımsız kabul

Süzgeç frekans cevabı, frekans taşıma, DC reddi, tam CI8/4096 çerçeve, retune
reset'i ve güvenli ofset negatifleri unit testlerle geçmiştir. Üç tekrarlı
1.024-kare kanal seçici+codec+bounded queue koşusu gerçek zaman eşiğini geçmiş;
sıra hatası, drop ve doyum sıfır kalmıştır. Protokol MSVC C11 decoder testini,
ağ köprüsü GCC C11 `-Werror` derlemesini ve WSL2 üzerinde gerçek TCP ile dört
istekli `SOCK_SEQPACKET` loopback entegrasyonunu geçmiştir.

## Fiziksel Ethernet kabulü

PC `192.168.7.1/24` ile ZedBoard `192.168.7.2/24` arasında doğrudan 1 Gbps/full
duplex bağlantı kurulmuştur. Köprü grup sonu beklemesi yerine en fazla dört
isteği sürekli uçuşta tutar, ağ işi CPU0'a bağlanır ve yerel istek payload'ı
ikinci kez kopyalanmadan `sendmsg` ile `SOCK_SEQPACKET` hizmetine iletilir.

Bilinen CI8 karesinin üç pozitif ve iki sıfır karelik yaşam döngüsü fiziksel
Ethernet→yerel hizmet→DMA→FPGA→ARM yolunda 54 aday için eşleşmiştir. Ardından
beş bağımsız koşuda toplam 20.480 ölçüm karesi tamamlanmıştır. En düşük/ortalama/
en yüksek hız `505,184524010 / 506,606589485 / 508,009093258 kare/s`, gereken
alt sınır `488,28125 kare/s` ve en düşük marj `1,034617905` olmuştur. Sıra hatası
ve aday düşümü sıfırdır. Kanıt `phase07-ethernet-physical-acceptance.json`
kaydındadır.

## Canlı uçtan uca kabul

Köprü ve açılış yapılandırması PetaLinux imajına alınmış; SHA-256 değeri
`5d749d4c2a8a86f2bbcc3be9a700ea32efc8104196b237700740886003e2e61d` olan
imajın soğuk açılışı sonrası FPGA `operating` ve kurulu köprü ikilisi doğrulanmıştır.
Değişken MAC tabanlı Linux adları tek fiziksel arayüzün `auto` seçimiyle çözülür;
sıfır veya birden fazla fiziksel arayüz fail-closed davranır. Köprü ürün imajında
güvenli varsayılan olarak kapalıdır ve bu kabulte açıkça etkinleştirilmiştir.
Tekrarlı kısa alımların yerine her koşuda tek `hackrf_transfer` stdout RX süreci
kullanılmıştır. USB okuma, stateful 8→2 MS/s kanal seçici ve dört-istekli ağ
taşıması üç ayrı sınırlı aşamada çalışır. İlk ardışık uygulama koşusunda gözlenen
10 USB overrun ve `485,291462661 kare/s` sonuç kabul edilmemiş; USB okuma ile
kanal seçimi ağ yanıt beklemesinden ayrılmıştır. Son beş koşuda 20.480/20.480
ölçüm karesi, sıfır USB overrun, sıfır sıra hatası, sıfır giriş/çıkış doyumu ve
toplam 32.927 FPGA adayı elde edilmiştir. En düşük hız `488,746900919 kare/s`,
gereken sınır `488,28125 kare/s`; 64-kare kuyruğun tepe kullanımı 8'dir.
PHASE-07 tamamlanmıştır. Bu kabul dBm kalibrasyonu, tespit olasılığı, saha yanlış
alarm oranı, yön bulma doğruluğu veya RF yayın işlevi iddiası oluşturmaz.
