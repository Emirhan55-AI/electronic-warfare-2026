# ADR-0043 — ET Faraday Laboratuvar Yetkilendirmesi

- Durum: Kabul edildi; fiziksel TX arka ucu ve donanım kabulü açık
- Tarih: 8 Eylül 2026
- Kapsam: KTR-5.1–5.3 kontrollü ET geliştirmesi ve kapalı RF doğrulaması
- Önceki karar: ADR-0023 çevrimdışı görev konsolu ve TX-kilitli modeller

## Bağlam

Kullanıcı, bundan sonraki fiziksel ET-TX çalışmalarının hazır korumaları bulunan
Faraday kabini içinde yapılacağını açıkça bildirmiştir. Bu beyan kontrollü
laboratuvar geliştirmesi için kalıcı ortam onayıdır; tek tek geliştirme
oturumlarında aynı ortam izni yeniden istenmez.

## Karar

`CABLED_LAB` için önceki genel politika kilidi kaldırılmıştır. Bu mod yalnız
Faraday kabini içinde, kabin dışına RF sızıntısı oluşturmayacak kapalı veya
kablolu/zayıflatıcılı düzende kullanılabilir. Genel `HARDWARE_TX_LOCKED` modu
açılmaz; açık alan, saha veya denetimsiz antenli TX bu kararla yetkilendirilmez.

Laboratuvar ortamı onayı çalışma zamanı interlocklarının yerine geçmez. Gerçek
TX başlatılmadan önce aşağıdakiler birlikte sağlanır:

1. TX ve bağımsız RX cihazları tam seri numarasıyla ayrılır.
2. Resmî ve doğrulanmış HackRF araçları kullanılabilir durumdadır.
3. Frekans, örnekleme, kazanç ve görev süresi sınırlandırılmıştır; ilk fiziksel
   koşu en düşük TX kazancında ve kısa sürede yapılır.
4. Operatör başlatması, süre sonunda otomatik durma ve gecikmesiz acil durdurma
   aynı oturumda çalışır.
5. Faraday kabini kapalıdır; kablolu düzende uygun zayıflatma bulunur ve bağımsız
   alıcı veya ölçüm cihazı sonucu kaydeder.
6. Komut, yapılandırma, cihaz kimliği, başlangıç/bitiş zamanı ve ölçüm çıktısı
   yeniden üretilebilir kanıt kaydına alınır.

Herhangi bir koşul eksikse TX fail-closed kalır. Kalıcı ortam onayı, eksik cihaz
veya interlockları yazılımla atlama izni değildir.

## Güncel Uygulama Durumu

`ETMissionController`, `CABLED_LAB` görev kabulünü açar ve görevi `FARADAY LAB`
bağlamıyla günlüğe yazar. Genel donanım modu hâlâ reddedilir. Ayrı C++17 sinyal
üreteci yalnız bellek içinde I/Q üretir. Sonraki PHASE-10 Tekli Görev çalışması
ürüne `HackRFTxRunner` süreç arka ucunu eklemiştir; bu yol kapalı güvenlik
profili, tam seri, izinli bant, ölçülmüş zayıflatma ve tarihli fiziksel kapı
olmadan `hackrf_transfer` başlatmaz.

8 Eylül 2026 denetiminde Windows üzerinde bağlı HackRF USB kimliği ve gerekli
HackRF host araçları gözlenmemiştir. Bu nedenle bu karar sırasında RF yayını
yapılmamış, fiziksel donanım yeteneği iddia edilmemiştir.

## Faz ve Kanıt Sınırı

Bu karar PHASE-10/11 için güvenlik hazırlığı ve kullanıcı onayıdır. Açık
PHASE-08 kapısını kapatmaz, PHASE-09'u tamamlamaz, fiziksel TX kabulünü geçmiş
saymaz ve yol haritasının sırasını değiştirmez. Donanım görünür olduğunda TX
arka ucunun fiziksel kabulü ayrı kaynak/cihaz özetleriyle yürütülür.

ADR-0023 kendi tarihindeki çevrimdışı ürün sınırının kaydı olarak korunur; güncel
`CABLED_LAB` yetki durumu için bu ADR geçerlidir.
