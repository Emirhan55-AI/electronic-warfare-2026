# ADR-0039 — PHASE-08 Yerel Kanal Seçici ve Görüntü Ritmi

- Durum: Sayısal eşdeğerlik ve host süre kapısı geçti; fiziksel USB tekrar kapısı açık
- Kapsam: 8 MS/s HackRF akışındaki 8→2 MS/s kanal seçici ve canlı spektrum/spektrogram sunumu
- Bağlı gereksinimler: KTR-4.1, KTR-4.1-OPS-B0
- Ön koşullar: ADR-0036, ADR-0038

## Bağlam

ADR-0036'nın NumPy referans kanal seçicisi doğru sonuç üretse de 2,048 ms giriş
periyodunun altında tekrarlanabilir yürütme payı bırakmıyordu. Aynı süreçte ham
8 MHz spektrum, waterfall ve host kaba aday çizimi çalıştığında Windows zamanlama
gecikmeleri USB akışını hassas hâle getiriyordu. Referans DSP davranışını veya
FPGA profilini değiştirmeden host hesap yükünün azaltılması gerekiyordu.

## Karar

193 tap simetrik FIR/NCO/4:1 örnek azaltma C++17 ile uygulanır. AVX2 ve FMA3
yolunda simetrik tap çiftleri birlikte hesaplanır. Her giriş karesi yine
16.384 kompleks CI8 örnek, her FPGA karesi yine 4.096 kompleks CI8 örnektir;
passband, stopband, tuning ve nicemleme sözleşmesi değişmez. C++ çekirdeği yalnız
host kanal seçicidir; Hann/FFT/OS-CFAR/geniş bant FPGA SystemVerilog zincirinin
yerine geçmez.

Yerel çekirdek yalnız sonlu, 193 elemanlı ve tam simetrik tap kabul eder. Çalışma
zamanı AVX2/FMA3 desteğini başlamadan doğrular. Fiziksel `HackRFContinuousRX`
yolunda derlenmiş çekirdek yoksa ürün NumPy referansına sessizce düşmez; sonuç
üretmeden `native_channelizer_required` hatası verir. Paketleme girdisi Release
DLL'yi `algorithms/p0/native/bin/p0_channelizer.dll` konumuna alır.

Windows'ta HackRF alt süreci normalin üzerinde öncelikte tutulur. Mantıksal CPU
numarasına göre varsayım yapmak yerine işletim sisteminin fiziksel çekirdek
maskeleri okunur; son üç fiziksel çekirdek alım sürecine, kalanlar uygulamaya
ayrılır. HackRF aktarım ve çıkış iş parçacıkları için üç çekirdekli ayrım, tam
arayüz yükü altında USB taşmasını önlemek üzere seçilmiştir. Bu işlem USB
denetleyicisini veya başka aygıtları yeniden yapılandırmaz.

Canlı görünüm 15 DSP karesinde bir, nominal 32,55 Hz beslenir. Spektrum ve
waterfall verisi her taze görünümde güncellenir; sabit grid/etiket Canvas
katmanları yalnız seçim, tespit, ölçek veya imleç değiştiğinde yeniden çizilir.
Tek bekleyen GUI bildirimi son görünümü korur; tespit veya USB kaybı düşürülmez.

## Sayısal ve süre kabulü

Beş kilitli tuning ofsetinde 16'şar ardışık rastgele kare, NumPy referansına
karşı toplam 80 karede sıfır CI8 LSB farkıyla geçmiştir. 2.000 çağrılık bağımsız
ölçümde p50 `0,295650 ms`, p95 `0,524815 ms`; giriş periyodu `2,048 ms`'dir.
Kaynak ve DLL SHA-256 bağlı kayıt
`results/evidence/phase08/native-channelizer-v3.json` dosyasındadır. Bu mikro
ölçüm bütün uygulamanın veya USB yolunun gerçek zaman kabulü değildir.

Görüntü katmanı düzeltmesinden sonraki güncel 60 saniyelik koşu 32,15 taze
görüntü/s, 40,04 ms p95 çizim aralığı ve 20,72 ms p95 alımdan sunuma yaş ile
görüntü hedeflerini geçti. Ancak HackRF üç shortfall, en uzunu 7.328 bayt,
bildirdiği için koşunun genel sonucu başarısızdır. Kaynak/DLL bağlı başarısızlık
kanıtı `results/evidence/phase08/live-rx-display-8msps-v2.json` dosyasındadır.

## Fiziksel USB sınırı

Aynı cihazla uygulama, FFT ve kanal seçici olmadan yapılan 8 MS/s, 60 saniyelik
`hackrf_transfer → NUL` kontrolü de bir adet 832 bayt shortfall üretmiştir.
`hackrf_info`, aygıtın dört başka USB aygıtıyla aynı veri yolunda olduğunu ve
donanımın Great Scott Gadgets üretimi görünmediğini bildirir. HackRF One USB 2.0
High-Speed aygıttır; USB 3.x porta takılması SuperSpeed aygıta dönüştürmez.
Başka port/kablo/host yoluyla A/B kontrolü yapılmadan bu kaynak sürümü için
tekrarlanabilir sıfır-taşma veya uzun süreli fiziksel kabul iddia edilmez.

## Açık kapılar

- HackRF'yi farklı fiziksel port ve bilinen iyi veri kablosuyla bağlayıp önce
  doğrudan, sonra ürün yolunda en az iki 60 saniyelik sıfır-shortfall koşusu.
- Aynı düzenle 15 dakika kaynak/DLL bağlı RX/görüntü kabulü.
- Güncel ADR-0037 bitstream'i ve kart kabulü.
- Yetkili kontrollü RF düzeneğinde 2,4/5,8 GHz pozitif/negatifler, Pd, yanlış
  olay/dakika ve ilk tespit gecikmesi.
