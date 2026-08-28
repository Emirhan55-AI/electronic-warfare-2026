# ADR-0030 — P0 OS-CFAR Hücre Kararının PL'ye Taşınması

- Durum: Kabul edildi
- Kapsam: P0 sürekli işleme hızı düzeltmesi
- Bağlı gereksinim: KTR-4.1

## Sorun

ADR-0029 kabulünde optimize edilmiş yerel hizmet 4.096/4.096 kareyi hatasız
tamamlamış, ancak `116,33994 kare/s` ile gerekli `488,28125 kare/s` hızın
altında kalmıştır. Aynı süreçte ölçülen ortalama `5,700 ms` ARM süresinin
`4,790 ms` bölümü OS-CFAR hücre taramasıdır. DMA ortalaması `0,457 ms` olduğu
için yalnız DMA değişikliği bu açığı kapatmaz.

## Karar

Kanonik `P0_OS_CFAR_EXPONENTIAL_PFA_1E4` hücre kararı PL'ye taşınır. Yöntem ve
sayısal profil değişmez: 16 referans/yan, 4 koruma/yan, yükselen 24/32 sıra
istatistiği, tam pencere kenar politikası ve strict `CUT > alpha × X_(24)`.

Çekirdek natural-order 58-bit `UQ28.30` güç karesini toplar, shifted sırada
kayan 41-bin pencere kurar ve iki sıralı 16-hücre kümesini her CUT için exact
silme/ekleme ile günceller. Birleşik 24. sıra istatistiği iki sıralı kümenin
sabit sınırlı ikili bölünmesiyle seçilir. Eşik katsayısı Q32 olarak
`36.851.433.755 / 2^32` değeridir. Karar doğrudan geniş tam sayı
karşılaştırmasıyla verilir; ara eşik kırpılmaz veya doyurulmaz.

DMA çerçevesi `4096 × 64 bit = 32768 byte` olarak kalır. Her çıkış kelimesinde
alt 58 bit exact güçtür. Üst bitler `0xA` biçim işareti, `detected` ve
`evaluated` alanlarını taşır. ARM biçim işaretini bütün karede doğrulamadan PL
kararını kullanmaz. Böylece güç karesi parametre çıkarımı ve geniş bant kurtarma
için korunurken OS-CFAR'ın tam-frame ARM taraması kaldırılabilir.

Bu aşamada yalnız OS-CFAR hücre değerlendirmesi PL sahibidir. Aday gruplama,
ADR-0028 geniş bant kurtarma, 2/3 zamansal doğrulama ve parametre çıkarımı
PS/ARM'da kalır. PHASE-06G bölgesel detector P0 OS-CFAR yerine geçirilmez.

## Önceden kilitlenen kapılar

- Python tam sayı modeli ile RTL'nin 64-bit çıkış kelimeleri bit-doğru eşleşir.
- Dondurulmuş PHASE-06F gerçek güç karelerinde mevcut float64/C OS-CFAR ile
  değerlendirme ve karar farkı sıfır olur.
- Strict eşik altı/üstü, tekrarlı referans değerleri, shifted kenarlar, reset,
  backpressure ve bozuk `TLAST/index` yolları sınanır.
- 50 MHz'te tek kare kabulünden son çıkışa üst sınır `102.400` çevrimdir; bu
  yalnız RTL kapasite kapısıdır, kart üzerindeki hizmet hızının yerine geçmez.
- Vivado sentez, route, setup/hold, kaynak ve bitstream sonuçları ayrı kaydedilir.
- ADR-0029'un `488,28125 kare/s` fiziksel hizmet kapısı değiştirilmez.

## Uygulama sonucu

Bit-doğru RTL kabulünden sonra çekirdek uzun karşılaştırma ve sıralama yolları
ayrı çevrimlere bölünerek boru hatlı uygulanmıştır. Vivado 2025.2 ile
`xc7z020clg484-1` üzerinde tam FFT→güç→OS-CFAR zinciri yerleştirilip
yönlendirilmiştir. 50 MHz koşulunda setup marjı `+2,400 ns`, hold marjı
`+0,050 ns`, setup/hold başarısız uç sayısı ve route hata ağı sıfırdır. Son
kullanım 17.387 LUT, 13.769 register, 21 BRAM tile ve 45 DSP'dir. Standalone
uygulama üstü board pinlerini içermediği için `NSTD-1` ve `UCIO-1` uyarıları tam
block design I/O katmanında çözülmek üzere kapsam dışıdır; başka DRC kritik
uyarısı veya DRC hatası yoktur.

Avnet ZedBoard `1.5` kart tanımıyla kurulan PS7+DDR+AXI DMA+çekirdek tam block
design da 50 MHz'te yerleştirilip yönlendirilmiştir. Tam tasarımın setup marjı
`+0,372 ns`, hold marjı `+0,018 ns`; başarısız setup/hold ucu, route hatası,
DRC hatası ve DRC kritik uyarısı sıfırdır. 19.587 LUT, 17.183 register, 23,5
BRAM tile ve 47 DSP kullanılmış; bitstream ile bitstream içeren XSA başarıyla
üretilmiştir. Bu sonuç fiziksel kart yürütmesi veya hizmet throughput kabulü
değildir.

Bu XSA ve güncel PS kaynakları PetaLinux 2025.2 projesine içe aktarılmıştır.
`p0-dma` paketi ile kök dosya sistemi 5.679/5.679, tam imaj 6.090/6.090 görevle
hatasız derlenmiş; ARM hizmet araçlarını içeren `image.ub` ve yeni PL
bitstream'ini içeren `BOOT.BIN` üretilmiştir.

Yeni imaj fiziksel ZedBoard üzerinde DONE, Linux, FPGA `operating`, DMA aygıtı
ve ayrıcalıksız yerel hizmet kapılarını geçmiştir. Bilinen karede alt 58 bitlik
4.096 güç değeri eski golden çıktı ile, işaret/değerlendirme/karar alanlarını
içeren 4.096 tam kelime ise Python tam sayı modeliyle sıfır fark vermiştir.
Hizmet beş karelik 2/3 geçici–doğrulanmış–sonlanmış olay dizisini sıfır hizmet,
sıra, DMA veya aday düşürme hatasıyla tamamlamıştır.

Sürekli hız kapısı geçmemiştir. Kilitli 64 ısınma + 4.096 ölçüm koşusunda bütün
kareler ve DMA `0x7` tamamlansa da hizmet `95,62877 kare/s` ölçülmüş; gerekli
`488,28125 kare/s` değerin yalnız `0,19585` katına ulaşmıştır. PL işaretini bilen
düzeltilmiş aşama profili 1.024 karede ortalama DMA `1,456537 ms`, ARM zinciri
`6,714248 ms` ve birleşik `8,170784 ms` ölçmüştür. ARM içindeki güç açma
`0,481628 ms`, PL aday gruplama `0,711251 ms`, PL sonrası çok ölçekli toplam
`1,559754 ms`; henüz ayrı ayrı araçlanmamış kalan zincir farkı `4,672866 ms`dir.
Bu nedenle ADR-0030 sayısal ve işlevsel olarak kabul edilmiş, fakat gerçek-zaman
amacını kapatamamıştır. Sonuca göre profil, örnekleme hızı veya kabul karesi
değiştirilmemiştir.

Bir kapı geçmezse OS-CFAR profili, örnekleme hızı veya kabul karesi sonuca göre
değiştirilmez. Eski fiziksel imaj, yeni imaj bütün host/RTL/Vivado kapılarını
geçmeden değiştirilmez.

## İddia sınırı

RTL simülasyonu veya Vivado zamanlama sonucu FPGA üzerinde çalışmayı kanıtlamaz.
Fiziksel sayısal eşdeğerlik başarıyla, sürdürülebilir hız ise başarısız sonuçla
kaydedilmiştir. Canlı RF, kalibrasyon, Ethernet ve RF yayın bu kararın kapsamı
dışındadır; gerçek-zaman başarısı ilan edilmez.
