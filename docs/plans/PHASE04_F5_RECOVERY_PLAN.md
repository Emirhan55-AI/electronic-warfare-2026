# PHASE-04-F5 OBW Zamansal Dayanıklılık Planı

## Amaç

Başarısız F4D kanıtını değiştirmeden, OBW99 geçerliliğinin seed ve sinyal ailesi
genellemesini güçlendirmek ve tamamen yeni veri ayrımıyla doğrulamak.

F5, F4D'nin yeniden koşusu değildir. F1-F4 binding/OOS popülasyonları yöntem
geliştirme veya eşik ayarı girdisi olamaz.

## Ürün ve FPGA sınırı

F5E ürün entegrasyonu, yalnız binding ve OOS kapılarının tamamını geçen host
parametre alanlarını digest bağlı, fail-closed ürün profilinde etkinleştirir.
Bu adım PHASE-04 kestirimcisini FPGA RTL'ye taşımaz ve yeni bitstream üretmez.
FPGA/PL-PS bütünleştirmesi PHASE-06/07 donanım hattında ayrı kaynak, timing,
DMA ve kart kabul kanıtı gerektirir.

## Alt fazlar

| Alt faz | Kapsam | Çıkış kapısı |
|---|---|---|
| PHASE-04-F5A | F4D salt-okunur kök neden analizi | F4D kararları yeniden üretilir; OBW temporal ret sınıfı ve geliştirme/OOS güvenlik payı açığı makine kanıtıyla ayrılır. |
| PHASE-04-F5B | Yeni protokol, veri ayrımı ve commitment kilidi | Yeni açık seed'ler F1-F4'ten ayrılır; binding/OOS preimage'ları yöntemden önce kapatılır; mevcut eşikler gevşetilmez. |
| PHASE-04-F5C | Ayrı v6 OBW zamansal dayanıklılık yöntemi | Aile ve seed bazlı OBW geçerlilik payı; doğruluk, clipping, gürültü ve span kontrolleriyle birlikte geçer; yöntem reveal öncesi kilitlenir. |
| PHASE-04-F5D | Çalıştırıcı kilidi ve tek seferlik değerlendirme | Commit/push sonrası seed reveal; binding ve OOS bir kez çalıştırılır; sonuç değişmeden korunur. |
| PHASE-04-F5E | Digest bağlı host ürün entegrasyonu | Yalnız bütün zorunlu alanlar iki popülasyonda da geçerse profil oluşturulur. |

## F5A bulguları

- F4D binding 40/40, OOS 23/24 geçmiştir. Tek ihlal OBW aile minimum
  geçerliliğinin 62/64 yerine 61/64 kalmasıdır.
- AM, OOK ve BPSK OOS popülasyonlarında 61/64 geçerli OBW üretmiştir.
- Merkez, güç ve SNR her ailede 64/64 geçerli; OBW clipping sayısı sıfırdır.
  Kalan ret sınıfı `obw_temporal_instability` olarak ayrılmıştır.
- OBW yöntemi v3, v4 ve v5 boyunca değişmemiştir. Önceki OOS minimumları
  sırasıyla 62, 63 ve 61'dir; sorun seed genelleme payıdır.
- Açık geliştirme aile kapısı %90 iken OOS aile kapısı %96,875'tir. F3/F4 ek
  kapılarında seed bazlı OBW geçerlilik güvenlik payı bulunmamaktadır.
- F4 geliştirmesinde AM ve BPSK 371/384 ile OOS oranına eşdeğer 372/384
  düzeyinin altında kalmıştır; mevcut düşük geliştirme eşiği bunu engellememiştir.
- Saklanan F4D kanıtı trial bazlı temporal range ve recovery dalı kaydetmediği
  için kesin alt neden yeniden koşu yapılmadan ayrıştırılamaz. Bu tanılar yalnız
  yeni açık F5 geliştirme popülasyonunda üretilecektir.

## F5B protokol gereksinimleri

- Yeni açık geliştirme seed'leri F1-F4 açık ve reveal popülasyonlarından bağımsız
  olmalıdır.
- Yeni binding/OOS seed ve salt değerleri v6 kaynakları oluşmadan önce repository
  dışında üretilip commitment olarak kilitlenmelidir.
- F2'nin 40 binding ve 24 OOS kontrolü gevşetilmemelidir.
- OBW geliştirme kabulü aggregate oranla yetinmemeli; aile ve seed bazlı minimum
  geçerli sayısı OOS kapısından daha güçlü bir güvenlik payı sağlamalıdır.
- Her ret için temporal range, recovery denemesi, recovery sonucu ve ret nedeni
  geliştirme kanıtında sayılmalıdır.
- Gürültü yanlış-geçerli sayısı sıfır; clipping sınırı sıfır kalmalıdır.
- Dört kare, tek worker, tek pending intent ve 65.536 bayt kalıcı yük sınırı
  korunmalıdır.

## Onay kapıları

F5A tamamlanınca F5B için yeniden kullanıcı onayı alınır. Aynı kural F5C, F5D
ve F5E geçişlerinde uygulanır. Tek seferlik değerlendirme başarısız olursa aynı
popülasyon yeniden çalıştırılmaz.

## Durum

PHASE-04-F5A, F5B ve F5C kullanıcı onayıyla tamamlanmıştır. F4D sonucu yeniden
üretilmiş; OBW temporal ret sınıfı, seed genelleme payı ve geliştirme/OOS kapı
uyumsuzluğu doğrulanmıştır. Sekiz yeni açık geliştirme seed'i F1-F4
popülasyonlarından ayrılmış, yeni binding/OOS preimage'ları commitment ile
kapatılmıştır. Korunan 18 geliştirme kontrolüne yedi OBW güvenlik kontrolü ve
altı zorunlu tanı eklenmiştir. Aile başına 379/384 ve seed başına 47/48 geçerli
OBW şartı yöntemden önce kilitlenmiştir.

F5C'nin ilk açık geliştirme deneyi 3,0; 3,25; 3,5; 4,0 ve 5,0 bin
temporal-recovery üst sınırlarını aynı 3.072 ölçümde karşılaştırmıştır. Hiçbir
aday kilitli kapıların tamamını geçmemiştir. 5,0 bin adayı aile minimumunda
377/384, seed minimumunda 46/48 kalmış; NFM üst kenar q95 hatası 2 bin sınırını
aşmıştır. Basit eşik genişletmesi seçilmemiştir. Sonraki yapısal çalışma NFM
kenar yanlılığı ile temporal recovery'yi birlikte ele almıştır.

Yapısal F5C çalışması dört kare gürültü-çıkarılmış spektrum ortalamasını,
%0,75 kuyruk oranını ve 0,375 bin simetrik kenar yanlılığı düzeltmesini
seçmiştir. 7 bin temporal ret sınırıyla sekiz ailenin her birinde en az 383/384,
her seed'de en az 47/48 geçerli OBW korunmuştur. En kötü göreli q95 hata %14,
alt/üst kenar q95 hataları 1,87/1,92 bindir. 3.072 ölçümde dört uç örnek açıkça
`obw_temporal_instability` olarak reddedilmiştir. Birleşik geliştirme sonucu 40
temel, 14 F3, dört F4 ve yedi F5 kontrolünün tamamını geçmiştir; altı gürültü
yanlış-geçerli sayısı sıfırdır. v6 yöntem `method-lock-v6.json`, tek-seferlik
çalıştırıcı `evaluation-runner-lock-v6.json` ile seed reveal öncesinde
kilitlenmiştir. F5D başlatılmamış, binding/OOS seed'leri açılmamış ve ayrı
kullanıcı onayı beklemektedir.
