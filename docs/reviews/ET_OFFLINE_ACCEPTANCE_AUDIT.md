# ET Offline Kabul Denetimi

- İş paketi: `ET-A`
- Tarih: 2026-08-26
- Kapsam: KTR-5.1–5.4 için donanımsız host modeli, yerel döngü ve güvenlik sınırı
- Doğrulayıcı: `scripts/verify_p0_et.py`
- Kanıt: `results/evidence/p0/et-golden.json`

## Sonuç

Mevcut ET kaynakları boş bir gösterim değildir; ancak dört görev aynı olgunlukta
değildir. Sürekli dalga biçimleri ile analog modülasyon kompleks taban bant
örneği üretir. Arabakışlı bölüm yalnız deterministik analiz girişi üzerinde görev
kararı verir ve çıkış dalga biçimi üretmez. GPS L1 C/A bölümü ise yalnız metadata
sözleşmesini doğrular; ephemeris, navigasyon mesajı, PRN kod üretimi veya I/Q
dalga şekli içermez.

| KTR | Doğrulanan mevcut yetenek | Açık sınır |
|---|---|---|
| KTR-5.1 | Tekli, çoklu, baraj ve doğrusal süpürme offline kompleks taban bantları; sonlu değer, tepe normalizasyonu, spektral yapı, baraj bant içi güç ve süpürme ilerlemesi | Zamanlanmış RF çıkışı, güç/etki ölçümü ve kapalı düzen kabulü yok |
| KTR-5.2 | `DİNLE → KARAR → GÖREV → KORUMA` denetleyicisi; hedef yok, sürekli, kesintili ve eşik-köşe analiz girişleri | Denetleyici çıkış örneği üretmez; gerçek zamanlayıcı, HackRF-2 ve görev çevrimi ölçümü yok |
| KTR-5.3 | AM/FM/NFM kompleks taban bant; 3 kHz ses bandı, tepe sınırı ve bağımsız yerel demodülasyon korelasyonu | Girdi 1 kHz doğrulama sesidir; gerçek kayıt/mikrofon iş akışı, alıcı ve RF kabulü yok |
| KTR-5.4 | GPS L1 C/A servis adı, konum, kesin UTC ve GPS'e ayrılmış 1–63 PRN kodu metadata denetimi | Dalga şekli, ephemeris/NAV veri işleme, alıcı testi ve RF çıkışı yok |

## Matematik ve sözleşme düzeltmeleri

OBW99 hesabı daha önce en güçlü FFT hücrelerini frekans sürekliliği olmadan
topluyordu. Bu yöntem iki kuyrukta eşit güç bırakma tanımını sağlamaz. Güncel
hesap, lineer güç toplamının alt ve üst tarafında ayrı ayrı `%0,5` bırakarak
`f2 - f1` sonucunu üretir. Yöntem, ETSI TS 125 141 bölüm 6.5.1.4.2'deki ölçüm
prosedürüyle uyumludur.

GPS alanındaki `uydu kimliği` ifadesi `GPS L1 C/A PRN kodu` olarak
netleştirilmiştir. Ocak 2026 GPS PRN tahsis tablosuna göre GPS için ayrılan L1
C/A aralığı `1–63` olarak doğrulanır. `+03:00` gibi zamanlar aynı anı UTC'ye
dönüştürebilse de senaryo sözleşmesi yalnız açık `Z` veya `+00:00` kabul eder.
Metadata geçmesi artık dalga şekli sözleşmesi geçmiş gibi raporlanmaz;
`waveform_available` daima `false` kalır.

Arabakışlı sınıfın bir karıştırma dalga şekli ürettiği izlenimi kaldırılmıştır.
Asıl ad `InterleavedTaskController`, üretilen veri `analysis_samples` ve görev
sonucundaki çıkış örnek sayısı sıfırdır. Eski sınıf adı yalnız mevcut laboratuvar
çağrılarını kırmayan uyumluluk takma adı olarak kalır.

## Kaynaklar

- ETSI TS 125 141, 6.5.1: <https://www.etsi.org/deliver/etsi_ts/125100_125199/125141/11.06.00_60/ts_125141v110600p.pdf>
- GPS resmî arayüz belgeleri: <https://www.gps.gov/interface-control-documents-icds-interface-specifications-iss>
- GPS L1 C/A PRN tahsisleri: <https://www.gps.gov/pseudorandom-noise-code-assignments>

## Güvenlik ve faz sınırı

`CABLED_LAB` ve `HARDWARE_TX_LOCKED` modları çalıştırma isteğini reddeder.
Acil durdurma kilidi sıfırlanmadan yeni görev başlamaz ve görev denetleyicisinde
`transmit` yöntemi yoktur. ET-A, PHASE-10–12'yi başlatmaz veya tamamlamaz; yalnız
önceden izin verilmiş offline P0 kaynaklarını ortak ve tekrarlanabilir kabul
kapısına bağlar.
