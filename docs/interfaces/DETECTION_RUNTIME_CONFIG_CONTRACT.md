# Çalışma sırasında tespit yapılandırması

11 Eylül 2026 · ST-06 · KTR-4.1 / KTR-4.1-OPS-B0

## Değişken FFT için kanıtlanan sınır

`scripts/probe_st06_runtime_fft.tcl`, mevcut sabit 4096 XFFT ile aynı
özelliklere sahip azami 16384 ve çalışma zamanı uzunluk seçimi açık XFFT'yi
aynı Vivado 2025.2 projesinde OOC sentezler. `scripts/verify_st06_runtime_fft_feasibility.py`
özellikleri ve kaynak raporlarını denetler. Dinamik çekirdek 4096/8192/16384
uzunluklarını NFFT 12/13/14 ile seçebilir; yapılandırma veri yolu 8 bitten
16 bite çıkar ve indis alanının 14 biti kullanılmalıdır.

Çekirdek bazında sabit/dinamik kaynakları sırasıyla 4.005/6.641 LUT,
7.196/9.947 register, 14,5/49 BRAM ve 30/38 DSP'dir. Mevcut tam tasarıma
ikame farkı eklendiğinde tahmini kullanım 22.531 LUT, 20.467 register,
58 BRAM ve 61 DSP'dir. Bu tarihsel kapasite fizibilitesi tam yerleştirme sonucu
değildi. Ardından tam ürün yolu uygulanıp yönlendirildi ve kartta doğrulandı.
[Ön kanıt](../../results/evidence/phase08/st06-runtime-fft-feasibility-20260910.json).

Gerçek uygulama tek atomik profil olarak ele alınır: seçilen uzunluk yalnız
DSP zinciri tamamen boşken kabul edilir; etkin NFFT karttan geri okunur;
Hann, FFT, güç/CFAR, DMA ve ARM aynı kare uzunluğunda olmalıdır. Uyuşmazlıkta
yeni I/Q kabul edilmez. DMA ABI v3, hizmet ABI v4 ve ağ çerçevesi giriş/çıkış
boylarını taşır. 8192/16384 güç hücreleri ARM'daki yerleşik 4096 olay ızgarasına
enerji korunarak ikiye/dörde indirgenir.

## Durum ve sınır

Kullanıcının FFT ve tespit ayarlarını gerçek FPGA/ARM yoluna bağlama isteği
ST-06 içinde tamamlandı. CFAR normal/zayıf katsayıları ile 4096/8192/16384 FFT
uzunluğu AXI kontrolü, Linux sürücüsü, ARM hizmeti ve arayüz uygulama/geri okuma
zinciri boyunca fiziksel kartta doğrulandı. Pencere türü Hann olarak sabittir.
Görüntü FFT seçimi ayrı sunum kontrolüdür.

Fiziksel post-downshift deneyi, XFFT'nin 8192'den 4096'a alınmasından sonraki
ilk veri transferinde DMA kilitlenmesi gösterebildi. Bu nedenle çalışma zamanı
profili bir açılış içinde yalnız aynı veya daha büyük FFT'ye uygulanır; küçültme
Linux sürücüsünde `EOPNOTSUPP` ile reddedilir. Kart yeniden başlatıldığında
profil 4096/kuşak 0'a döner. Profil geri okuması tek başına küçültme başarısı
sayılmaz.

`axis_p0_os_cfar` modülünde `RUNTIME_CONFIG=0` genel varsayılandır. Sabit üst
modül özgün çarpanları korur; güncel `p0_dsp_configurable_bd` kart varyantı
`RUNTIME_CONFIG=1` kullanır. Normal ve zayıf Q32 katsayıları aşağıdaki el
sıkışmasıyla uygulanır.

## Çekirdek bağlantısı

| Sinyal | Anlamı |
|---|---|
| `config_valid`, `config_ready` | Aynı saat kenarında 1 ise istek alınır |
| `config_fft_log2[3:0]` | 12/13/14 ile 4096/8192/16384 tespit FFT uzunluğu |
| `config_alpha_q32[35:0]` | Normal güç eşik katsayısı |
| `config_weak_alpha_q32[33:0]` | Zayıf aday güç eşik katsayısı |
| `config_applied` | Geçerli istek uygulandı; bir çevrimlik darbe |
| `config_rejected` | Geçersiz istek reddedildi; etkin profil korunur |
| `active_alpha_q32`, `active_weak_alpha_q32` | Çekirdeğin etkin katsayıları |
| `active_fft_log2[3:0]` | FPGA'nın gerçekten kullandığı ve geri okunan NFFT |

İstek yalnız sıfırlama bitmişken, ilk güç hücresi henüz alınmamışken ve giriş
geçerli değilken kabul edilir. Veri ile ayar çakışırsa veri önceliklidir.
Toplama, hesaplama, çıktı ve yeniden eşleme boyunca ayar alınmaz. Bekleme
sırasında isteği tutmak çağıranın sorumluluğudur; çekirdek meşgulken tek
çevrimlik istek uygulanmış sayılmaz. Üst seviye kontrol, I/Q kabulünü durdurup
önceki pencere/FFT/DMA ve ARM kuyruklarını boşaltmadan ayar uygulamamalıdır.
CFAR'ın boş olması bütün DSP zincirinin boş olduğu anlamına gelmez.

Katsayı aralıkları mevcut çarpan genişliğidir: normal `[1,16)`, zayıf `[1,4)`;
zayıf katsayı normalden büyük olamaz. Bu aralıklar RF doğruluk kabulü veya
operatöre açılacak önerilen aralıklar değildir. Reset özgün katsayıları
`36851433755` ve `17098572778` değerlerine getirir.

Başarılı SET sonrasında ARM boruhattı aynı normal/zayıf katsayıları alır;
zayıf olay eşik raporu etkin profil ile hesaplanır. PL değişip ARM güncellenmezse
hizmet fail-closed durur. Kuşak numarası eski istemcinin yeni profili ezmesini
engeller; belirsiz uygulama sonucu yeni I/Q işlemeye izin vermez.

## Doğrulama ve sonraki kapılar

`tests/test_cfar_runtime_config.py` tamsayı modeliyle dört profil/çerçevede
16.384 kelimeyi karşılaştırır. Geçersiz katsayılar, etkin değer geri okuma,
ilk örnekle çakışma, kare ortası istek, reset ve çıktı geri basıncı denetlenir.
`scripts/check_st06_weak_power_rtl.py` varsayılan yolun 49.152 kelimelik
referans karşılaştırmasını ve mevcut bozuk çerçeve kontrollerini yürütür.

Önceki `st06-weak-power-20260910.json` farklı kaynak/imajı kaydeder ve korunur.
Güncel yapı `st06-runtime-config-physical-20260910-v3.json` ile hash bağlıdır.
Fiziksel kartta kontrol/geri okuma/karar etkisi; arayüz yolu; sıfır, gürültü,
dar ton ve geniş bant sayısal koşulları; üç uzun hız tekrarı geçmiştir. En düşük
hız 507,587 kare/s, gereken hız 488,281 kare/s'dir. Bitstream WNS +0,234 ns,
WHS +0,011 ns ve yönlendirme hatası sıfırdır.

Dinamik FFT tam tasarımı WNS `+0,613 ns`, WHS `+0,030 ns`, sıfır yönlendirme
hatası ve cihaz kapasitesi içinde kaynak kullanımıyla geçti. Her boyut üç
bağımsız 4.096-kare kart koşusunda hedef hızını geçti; en düşük hızlar
540,081 / 249,970 / 138,120 kare/s'dir. Etkin profil geri okuması, başlangıç
profiline dönüş geri okuması, DMA/CRC/sıra/kuyruk bütünlüğü ve kart/yerel ürün
hash eşliği geçti. Sonradan yapılan post-downshift veri testi yukarıdaki sınırı
ortaya çıkardı; eski kayıt değiştirilmez.
[Tarihsel artan FFT kanıtı](../../results/evidence/phase08/st06-runtime-fft-physical-repeated-20260911.json),
[güncel kalıcı imaj ve küçültme koruması](../../results/evidence/phase08/parameter-persistent-image-20260911.json).

Güncel FPGA, sürücü, cihaz ağacı ve ARM hizmetleri SD `BOOT.BIN`/`image.ub`
imajına alınmış ve iki yeniden başlatmada doğrulanmıştır. Hann dışı pencere,
gerçek HackRF+GUI dayanıklılığı ve RF Pd/Pfa halen açık kabul kapılarıdır.
