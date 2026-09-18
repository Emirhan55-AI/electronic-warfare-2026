# Koşullu taşıyıcı frekansı kestirimi — 18 Eylül 2026

## Karar ve kapsam

KTR-4.2'nin mevcut onaylı parametre iyileştirmesi içinde, doğrudan gözlenen
taşıyıcı çizgisine ek olarak ayrı bir koşullu kestirim uygulanmıştır. Merkez
frekansı taşıyıcı alanına kopyalanmaz. Modülasyon türü, yayıcı kimliği veya
mutlak kalibre frekans bu sonuçtan çıkarılmaz; fiziksel KTR-4.2 kabulü açıktır.
Yöntem frekans ve örnekleme hızına göre çalışır; 820 MHz'e özgü sabit yoktur.

## Hesap ve retler

Yeni 16 özgün CI8 kare bağı korunur. PL'nin kare başına Hann → 4096 FFT →
UQ28.30 güç yolu değişmemiştir. ARM, seçili kanalın ham I/Q'sunu dört-hücre
kenar geçişiyle izole eder; ikinci/dördüncü kuvvetin 65536 noktalı Hann
periodogramında çizgi arar. Log-parabolik tepe düzeltmesi ve normalize koherent
konsantrasyon kullanılır. Bağımsız NumPy referansı aynı girdiyi işler; ürün
hesabı PC'ye geri dönmez. Temel yaklaşım
[kuvvet periodogramıyla frekans kestirimi](https://www.mathworks.com/help/comm/ref/coarsefrequencycompensator.html)
ile uyumludur; bu kaynak kendi kapılarımızın doğruluğunu kanıtlamaz.

Geçerli OBW kenarları ve bant içi SNR ≥ 6 dB gerekir. OBW ≥ örnekleme hızının
yarısında sonuç verilmez; OBW ≥ hızın dörtte birinde yalnız ikinci kuvvet
denenir. Alias dalı OBW orta noktasına göre seçilir. Aday bu noktadan en çok
`maks(2 FFT hücresi, OBW'nin %7,5'i)` uzak olabilir. Tam pencere konsantrasyonu
ikinci/dördüncü kuvvette ≥ 0,35/0,25; dört ayrı zaman grubunun her birinde
≥ 0,25/0,15 olmalıdır. Grup frekans aralığı ve tam pencereye uzaklık en çok
0,25 özgün FFT hücresidir. İki kuvvet geçip frekansları uyuşmazsa sonuç yoktur.
Doğrudan çizgi geçerliyse yeni kestirim çalıştırılmaz. Bellek hatası tüm isteği
güvenli biçimde reddeder. Geçici iki kompleks tampon toplam 2 MiB'dir;
kalıcı 16-kare parametre yükü 1.557.504 bayt olarak kalır.

Bu dar kapsam BPSK/QPSK ve gerçek-değerli bastırılmış taşıyıcı koşulları içindir.
FSK, genel OFDM, FM, QAM veya bilinmeyen her yayında taşıyıcı çıkarma garantisi
yoktur. İki simetrik ton, DSB ile aynı I/Q'yu oluşturabilir; bu temel belirsizlik
nedeniyle sonuç modülasyon doğrulaması değil **koşullu kestirim** olarak kalır.
Faz/simge senkronizasyonu veya demodülasyon uygulanmış sayılmaz.

## Protokol, kayıt ve arayüz

P0CQ yetenek biti `0x8`, 16-kare taşıyıcı kestirim desteğini bildirir; genişletilmiş
parametre desteği olmadan kabul edilmez. Yeni istemci yalnız bu bit varsa
P0PM-v5 gönderir. İstek boyutu 131136, yanıt boyutu 176 bayttır. Yanıtın 37.
baytı CRC korumalı köken bilgisidir: 0 doğrudan çizgi/eski anlam, 2 ikinci
kuvvet, 4 dördüncü kuvvet. Son iki durumda 144. bayttaki alan kestirimdir;
istemci bunu `recovered_carrier_frequency`, durum `uncertain`, yöntem
`frequency.suppressed-carrier-power-consensus-v1` olarak ayırır. Gözlenen çizgi
`not_observed` kalır. Eski P0PM-v1…v4 yanıtları bu alanı yeniden yorumlamaz.
Eski istemcinin bilinmeyen yetenek bitini reddetmesi beklenen güvenli davranıştır.

Arayüzde `Gözlenen Taşıyıcı Frekansı` ve `Taşıyıcı Frekansı Kestirimi` ayrı
satırlardır. Kestirim yaklaşık işareti ve `TAHMİNİ` durumuyla, birincil beyaz
metinde gösterilir; doğrulanmış sayısal alan sayısına eklenmez. Kestirim yoksa
ek satır görünmez. Kayıt kökeni/yöntemi saklar ve özgün kart yanıtından tekrar
üretilir. dBm kalibrasyon kapısı ve deneysel Analog/Sayısal model bağı değişmez.

## Tekrarlanabilir kanıt

`output/parameter-review-20260918/carrier-recovery-c-v3.json`: 66 C/NumPy
karşılaştırması geçti, 21 koşullu kestirim üretildi. 2 ve 8 MS/s, 431 MHz merkez,
BPSK/QPSK/DSB, iki SNR ve üç ayrı tohum kullanıldı. 12 dB'de bu üç aile
18/18 kestirildi; 6 dB girişlerin 18/18'inde tam ARM kalite/kestirim bağı
sonuç vermedi. Bu kapsam kaybı gizlenmez. Denenen FSK, gürültü-benzeri yayın,
frekans sıçraması, dairesel gürültü ve düşük SNR negatifleri kestirilmedi.
913 MHz merkezli ayrı geniş bastırılmış taşıyıcı ile iki gerçek kayıt geçti.
Verilen sentetik frekansların hatası < 0,05 hücre, C/NumPy farkı < 0,01 Hz;
bu sayısal üretici karşılaştırmasıdır, fiziksel frekans doğruluğu değildir.

ARM ikilileri çalışan karta geçici yüklendi; SD/BOOT.BIN/imaj değiştirilmedi.
Hizmet SHA-256 `99d87146a7d41058fbc2e7c62f65114d55e7f4f23e6c261958dc09c959e98e8c`,
köprü SHA-256 `58988d6cf551ac71512bb9be96a369429e5adae3f69508a03aac6d6f5685b0f3`.
Kaynak/derleme bağı `build/p0/parameter-20260918/software-carrier-v1/build.json`.
Çalışan ikililerin hash'leri SSH üzerinden kurulum öncesi/sonrası doğrulandı;
önceki ikililer `/tmp/parameter-before-20260918-carrier-v1/` altında korunur.

Gerçek PL/ARM'da `real-820-carrier-board-v1.json` taşıyıcı kestirimini
`819,999903919 MHz`, merkezini `820,031321536 MHz`, OBW'yi `684,373127 kHz`
verdi (621690 µs). `real-new820-carrier-board-v1.json` bağımsız gerçek kayıtta
`819,999971866 MHz` kestirim, `820,144998248 MHz` merkez ve `674,851346 kHz`
OBW verdi (624306 µs). İkisinde de doğrudan çizgi gözlenmedi. Altı normal
parametre kart sahnesi `board-numeric-carrier-v1.json`, sekiz yön protokol
sahnesi `board-direction-carrier-v1.json` ile geçti.

Yeni canlı deneme `live-820-carrier-v1.json` 16-kare kayıt üretimini tamamladı,
ancak 4,467 dB gürültü referans farkıyla alanlar reddedildi. Dosyadaki `passed`
yalnız eski yürütücünün işlem tamamlandı etiketidir; sayısal/RF başarı değildir.
Yürütücü artık geçersiz zorunlu alanları `inconclusive` sayar. İkinci deneme
`live-820-carrier-v2.json` HackRF başka canlı alımda kullanılırken cihaz
erişiminde durdu. Bu koşular olumlu kayıtlarla değiştirilmez. Yeni canlı RF'de
kestirim görünürlüğü, daha geniş aile kapsamı, referans cihaz doğruluğu ve
soğuk açılış kalıcılığı açık kapılardır. PHASE-08/ST-06 kabulü değişmemiştir.

Kaynak, ikili, CRC'li çalışan kart yeteneği ve altı raporun bütünlüğü
`scripts/verify_carrier_deployment_evidence.py` ile doğrulanır; sonuç
`output/parameter-review-20260918/carrier-deployment-evidence-v2.json` içindedir.
Yeni canlı iki koşunun geçerli ölçüm sayısı bu raporda açıkça sıfırdır.
Parametre/protokol/canlı oturum/ürün regresyon grubunda 229 test geçti;
kestirim satırı, model sayımı ve sade etiketler için üç QML testi ayrıca geçti.
`tests/p0/test_p0_ed_service.py` grubunda altı eski kaynak/kanıt/sabit metin
kontrolü başarısız kaldı. Tarihsel hash'ler değiştirilmedi ve bu kapılar yeni
ikili kabulüne çevrilmedi. Bütün depo testleri geçti iddiası yoktur.

Yeni canlı reddin ek aralık tanısı: otomatik genişleyen span `[208,3251]`
sol referansı çıkış merkezine göre yaklaşık `−916…−901 kHz`, sağ referansı
`+590…+605 kHz` konumuna taşıdı. Kanal filtresinin düz geçiş sınırı `±800 kHz`.
Dolayısıyla sol referans düz geçişin dışında, sağ referans içindedir; bu
geometri referans farkına katkıda bulunabilir. Ham kayıttaki güçler de önceki
kayıttan farklıdır; yalnız yayını veya yalnız filtreyi kesin kök neden ilan
etmek için yeterli kanıt yoktur. Sinyali zorla kırpan daha dar bir span seçilip
ret başarıya çevrilmedi. Sonraki canlı kapı, referansları düz geçişte tutan
alıcı/analiz konumu ve tam emisyon kapsamasıyla birlikte doğrulanmalıdır.
