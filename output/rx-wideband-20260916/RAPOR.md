# 1 MHz–6 GHz tarama gözlemi — 16 Eylül 2026

Tarama canlı uygulamadan başlatıldı. Profil: 10 MS/s geniş bant burst,
LNA/VGA 24/24 dB, AMP kapalı, 128 kare/pencere ve 8 yerleşme karesi.
Alıcı seri sonu `36877e47`. Dış vericinin frekansı ve yayın zamanları bağımsız
olarak kaydedilmedi; gözlemler belirli bir test vericisine bağlanamaz.

İlk kontrol noktasında 366/2400 pencere, 1–916 MHz kapsam ve 82 ham gözlem
vardı. Tur devam ediyordu; tam bant sonucu değildir. Tamamlanan ana alımlar ve
kabul edilen ikinci ayar sonuçlarında USB overrun, CRC/sıra/kuyruk hatası ve
kırpılma sıfırdı. Bununla birlikte ilk iki pencerede `iq_saturation` nedeniyle
kazanç tekrarı yapıldı. Başarılı sonuçların sıfır sayaçları bu tekrarları silmez.

## Listeyi okuma

- Satırlar tur boyunca biriken geçmiş RF gözlemleridir; verici sayısı değildir.
- Frekans adayın hesaplanan merkezidir; geniş adayda en güçlü çizgi farklı olabilir.
- Tespit aralığı ölçülmüş işgal bant genişliği değildir.
- İki alıcı ayarında eşleşme, kaynağın haricî/bağımsız bir verici olduğunu kanıtlamaz.
- Tur sonundaki tekrar kontrolü ayrı bir zamandaki gözlemdir; alınmama sonucu
  vericinin kesin kapandığını kanıtlamaz.

Arayüz bu kayıtları üç kullanıcı bölümünde gösterir: `Yüksek güvenli adaylar`,
`Tekrar ölçülmesi gerekenler` ve `Alıcı etkisi olabilecekler`. Satır mesajları
teknik yöntemi tekrarlamak yerine önce incelemeyi, yeniden ölçmeyi veya yayın
olarak kabul etmemeyi söyler. Bölüm adları verici kimliği ya da kesin parazit
kararı değildir. Aralığı bulunan tüm kayıtlarda `Tespit aralığı` satırı gösterilir;
1 kHz'den dar çizgilerde kenar değerleri dört ondalık MHz ile korunur.

## Somut bulgular

1. Liste her kayıt artışında başa dönüyordu. Kaynakta bu davranış kaldırıldı.
   Kayıt sayısı, geçmiş bilgisi ve normal turda frekans sırası gösterildi;
   frekanslar Türkçe biçimde üç ondalık MHz ile sunuldu. Tam değer kayıtta kaldı.
2. `observed_frames` gerçek kare sayısını aşabiliyor: `3:0` kaydı
   10,032666 MHz'te 125; `39:0` kaydı 99,623207 MHz'te 160 sayıyor.
   Her pencerede yalnız 120 değerlendirilebilir kare var. Kodda aynı karedeki
   ayrı gruplar geçmişteki aynı geniş kayda eşleşerek sayacı tekrar artırabiliyor.
   Bu hata henüz düzeltilmedi; süreklilik oranı için güvenilir değildir.
3. İlk kontrol noktasında beş geniş adayın ikinci ayar aralığı ilk aralığın
   onda birinden küçüktü. Örneğin 10,032666 MHz adayının yaklaşık 670,5 kHz
   aralığı ikinci ayarda yaklaşık 0,632 kHz çizgiyle eşleşti. `_verification_matches`
   küçük aralığa göre örtüşmeyi kabul ediyor. Bu, geniş yayının bütününü doğrulamaz;
   kesin yanlış alarm sınıflaması için yeterli kanıt değildir.
4. Sunum birleştirmesi yalnız komşu pencerelerdeki dar çizgilere uygulanıyor.
   Geniş ve örtüşen aralıklar ayrı kalıyor. Bu nedenle satırları sayarak yayın
   sayısı elde edilemez. Sabit 2 MS/s hücre toleransı da 10 MS/s ana tarama
   çözünürlüğünü temsil etmiyor; bu inceleme algoritmayı değiştirmedi.

İstenen “Tespit ve alıcı spektrumu uyumlu” alt yazısı kaynakta kaldırıldı.
Gerçek QML ve tarama sunumu testlerinde 44 test geçti. Aktif turu kesmemek için
uygulama yeniden başlatılmadı; yeni arayüz çalışan turda yüklenmedi.

Canlı audit `build/acceptance/rx-survey/1de7f3a9efe041398957c8784acd78e2.jsonl`.
`analyze_scan.py` tekrar çalıştırılarak güncel kontrol noktası ve SHA-256 alınır;
`scan-analysis.json` tamamlanmadan önce değişen kontrol noktasıdır.
Çalışan süreç/kart imajı kaynak eşleşmesi bağımsız doğrulanmadı. Bu gözlem
yeni kaynağın fiziksel kabulü değildir; PHASE-08/ST-06 ve KTR-4.1 kabulü açıktır.

## Kullanıcı isteğiyle durdurulan tur — 16 Eylül 2026

Tur 863,065 saniyede kullanıcı isteğiyle durduruldu (`cancelled`).
1963/2400 pencere tamamlandı; kesintisiz sorumluluk kapsamı 1–4908,5 MHz,
437 pencere taranmadı. 161 ham gözlem, sunum birleştirmesiyle yine 161 kayıt
oluşturuyor. Tur tamamlanmadığı için otomatik son tekrar kontrolü başlamadı;
tekrar görüldü/görülmedi sayısı yoktur. Takip duraklatıldı.

161 kaydın 60'ı (%37,3) 40 MHz'in tam katlarına ±10 kHz uzaklıkta:
80, 120, 160, 200 MHz ... 1760, 1800, 1840 MHz gibi. Bu tarak biçimli yapı
ortak saat/elektronik kaynak veya harmonik ailesi şüphesidir; alıcı içi mi,
haricî bir kaynak mı olduğu bu turla belirlenemez. Bu 60 kayıt keyfî biçimde
silinmedi veya kesin parazit olarak etiketlenmedi. Bunların 56'sının ikinci
ayar yöntemi FPGA, dördünün çok kareli RX'tir. Genel listede 112 FPGA ve
49 çok kareli RX ikinci ayar sonucu bulunur; tüm kayıtları FPGA doğrulaması
olarak okumak doğru değildir.

16 kaydın ilk aday aralığı yaklaşık 125,5 kHz veya daha geniştir. Sekizinde
ikinci ayar aralığı ilk aralığın onda birinden küçüktür. Örneğin 40,620850 MHz
kaydı 39,295–41,947 MHz; 41,257913 MHz kaydı 39,195–43,320 MHz aralığını taşır.
Bu iki örtüşen satırdan iki bağımsız yayın sonucu çıkarılamaz. Kare sayacı
hatası iki kayıtta korunmaktadır (125 ve 160; mümkün kare 120).

Tamamlanan ana alım ve kabul edilmiş ikinci ayar sonuçlarında CRC/sıra/kuyruk
hatası sıfırdır. Ancak tur genelinde ilk iki pencerede kırpılma sonrası kazanç
tekrarı ve 1674. indeksli pencerede `usb_overrun` sonrası bir taşıma tekrarı
vardır. UI'daki `0 hata` başarısız kalan pencere sayısıdır; turda hiç sorun
yaşanmadığı anlamına gelmez.

Özgün audit bu klasöre kopyalandı. SHA-256:
`138b61a31a181220e4dc1ccbd57ad40d8434aee0bbe3a0b6b8d6f9a5ffa6c52d`.
`final-manifest.json` son kapsamı, `signal-list.json` tam aday ayrıntılarını,
`scan-analysis.json` son analizi içerir. Yeni alım başlatılmadı. Kaynak/kart
imajı eşleşmesi doğrulanmadı; PHASE-08/ST-06 kabulü açık kalır.
