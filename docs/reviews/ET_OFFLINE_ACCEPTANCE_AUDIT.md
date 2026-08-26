# ET Offline Kabul Denetimi

- Güncel iş paketi: `ET-B`
- Tarih: 2026-08-26
- Kapsam: KTR-5.1–5.4 için donanımsız host modeli, yerel döngü, arabakışlı zamanlama ve güvenlik sınırı
- Doğrulayıcı: `scripts/verify_p0_et.py`
- Kanıt: `results/evidence/p0/et-golden.json`

## Sonuç

ET kaynakları gösterim amaçlı sahte sonuç üretmez; ancak dört görev aynı
olgunlukta değildir. Sürekli ve analog modeller kompleks taban bant örneği
üretir. Arabakışlı model, deterministik analiz girişi ile sınırlandırılmış
offline görev tamponunu ayrı zaman pencerelerinde üretir. GPS L1 C/A bölümü ise
yalnız metadata sözleşmesini doğrular; ephemeris, navigasyon mesajı, PRN kod
üretimi veya I/Q dalga şekli içermez.

| KTR | Doğrulanan mevcut yetenek | Açık sınır |
|---|---|---|
| KTR-5.1 | Tekli, çoklu, baraj ve doğrusal süpürme offline kompleks taban bantları; sonlu değer, tepe normalizasyonu, spektral yapı, baraj bant içi güç ve süpürme ilerlemesi | Zamanlanmış RF çıkışı, güç/etki ölçümü ve kapalı düzen kabulü yok |
| KTR-5.2 | Hedef yok, sürekli, kesintili ve eşik-köşe girdilerinde ayrık `DİNLE → GECİKME → GÖREV → KORUMA` pencereleri; görev maskesi, tepe sınırı, ton frekansı ve görev çevrimi | Host çevrimi gerçek zamanlı değildir; HackRF-2, RF TX, deadline/latency, RF güç/etki ve kapalı düzen spektrum ölçümü yok |
| KTR-5.3 | AM/FM/NFM kompleks taban bant; 3 kHz ses bandı, tepe sınırı ve bağımsız yerel demodülasyon korelasyonu | Girdi 1 kHz doğrulama sesidir; gerçek kayıt/mikrofon iş akışı, alıcı ve RF kabulü yok |
| KTR-5.4 | GPS L1 C/A servis adı, konum, kesin UTC ve GPS'e ayrılmış 1–63 PRN kodu metadata denetimi | Dalga şekli, ephemeris/NAV veri işleme, alıcı testi ve RF çıkışı yok |

## Arabakışlı zamanlama sözleşmesi

ET-B, analiz ile görev üretiminin eşzamanlı olduğu belirsiz önceki durum
makinesini zaman paylaşımlı pencere sözleşmesine çevirmiştir. Bant gücü yalnız
`DİNLE` penceresinde hesaplanır. Ardışık iki olumlu gözlemden sonra bir tam
`GECİKME` penceresi beklenir; ardından sınırlı `GÖREV` penceresi ve çıkışın
kapalı olduğu `KORUMA` penceresi gelir. Kalan kayıt süresi bu dizinin tamamına
yetmiyorsa yeni görev başlatılmaz.

Varsayılan kabul vektörü sekiz adet 512 örnekli pencere kullanır. Bir görev
penceresinde 512 örnek açılır ve ölçülen görev çevrimi `1/8 = %12,5` olur.
Örnek maskesi dışındaki kompleks çıkış tam sıfırdır. Görev penceresinde analiz
ölçümü bulunmaz; dinleme penceresinde de görev kapısı açılamaz. Üretilen tampon
yalnız matematiksel offline kanıttır ve herhangi bir SDR aktarım yoluna bağlı
değildir.

Bu model, yakalanan bir radar işaretini örnekleyip yeniden üreten
`interrupted-sampling repeater jamming` modeli değildir. Uygulanan kavram,
alım/algılama ile görev pencerelerini zaman içinde ayıran time-sharing denetim
modelidir. Böylece iki farklı literatür terimi aynı özellikmiş gibi raporlanmaz.

## Önceki matematik ve sözleşme düzeltmeleri

ET-A sırasında OBW99 hesabı, lineer güç toplamının alt ve üst tarafında ayrı
ayrı `%0,5` bırakacak biçimde düzeltilmiştir. Yöntem ETSI TS 125 141 bölüm
6.5.1.4.2'deki ölçüm prosedürüyle uyumludur.

GPS alanındaki `uydu kimliği` ifadesi `GPS L1 C/A PRN kodu` olarak
netleştirilmiştir. Ocak 2026 GPS PRN tahsis tablosuna göre GPS için ayrılan L1
C/A aralığı `1–63` olarak doğrulanır. Senaryo sözleşmesi yalnız açık `Z` veya
`+00:00` kabul eder. Metadata geçmesi dalga şekli sözleşmesi geçmiş gibi
raporlanmaz; `waveform_available` daima `false` kalır.

## Kaynaklar

- ETSI TS 125 141, 6.5.1: <https://www.etsi.org/deliver/etsi_ts/125100_125199/125141/11.06.00_60/ts_125141v110600p.pdf>
- GPS resmî arayüz belgeleri: <https://www.gps.gov/interface-control-documents-icds-interface-specifications-iss>
- GPS L1 C/A PRN tahsisleri: <https://www.gps.gov/pseudorandom-noise-code-assignments>
- Time-sharing alım/görev ayrımı: <https://www.mdpi.com/2072-4292/13/15/3043>
- Tepkili modelde yanıt gecikmesi: <https://www.mdpi.com/1999-5903/17/10/474>

## Güvenlik ve faz sınırı

`CABLED_LAB` ve `HARDWARE_TX_LOCKED` modları çalıştırma isteğini reddeder.
Acil durdurma kilidi sıfırlanmadan yeni görev başlamaz ve görev denetleyicisinde
`transmit` yöntemi yoktur. ET-B, PHASE-10–12'yi başlatmaz veya tamamlamaz. RF TX,
RF güç/etki, gerçek zamanlı donanım zamanlaması ve kapalı RF düzeni açık kalır.

## Çıkış regresyonu

ET-B doğrulayıcısındaki KTR-5.1, KTR-5.2, KTR-5.3, KTR-5.4 ve TX fail-closed
kapılarının beşi de geçmiştir. Tam depo regresyon sonucu, kanıt kaydıyla birlikte
bu bölümde güncellenir.
