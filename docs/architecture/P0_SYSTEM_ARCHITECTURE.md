# P0 Gerçek Sistem Mimarisi

## Bilgisayar-1 — ED / Operatör

HackRF-1 yalnız RX kaynağıdır ve USB ile Bilgisayar-1'e bağlanır. Bilgisayar-1
bounded `ci8` I/Q frame'lerini CRC'li, sıralı Ethernet sözleşmesiyle ZedBoard PS'ye
gönderir. PS DDR ve AXI DMA ile PL Hann→FFT→güç zincirini besler; güç frame'i PS'ye
döner. PS OS-CFAR, gruplama, temporal doğrulama, zorunlu parametreler ve manuel DF
durumunu üretir. PySide6 arayüzü sonuç nesnelerini görselleştirir.

PetaLinux hazır olana kadar aynı sözleşmeler host referans/oracle üzerinde
çalıştırılır. Bu geçici yürütüm PC'yi nihai algoritma sahibi yapmaz.

## Bilgisayar-2 — ET

Bilgisayar-2, HackRF-2 rolünden ve ET kontrolünden sorumludur. P0 yazılım kabulü
yalnız `OFFLINE` ve `LOOPBACK` modlarındadır. `CABLED_LAB` güvenlik/interlock
kanıtı olmadan kilitlidir; gerçek TX backend'i uygulanmamıştır.

İki bilgisayar Python belleği veya süreç durumu paylaşmaz. Gelecekte görev verisi
aktarılması gerekirse sürümlü ağ veya dosya sözleşmesi kullanılır.

## Anten ve DF

Seçilen frekansa uygun FOX-727, 800 MHz–6 GHz UWB veya HackRF bandıyla sınırlı
TEM yönlü anten operatörce elle döndürülür. Her ölçüm açı, göreli güç, frekans,
UTC zaman ve güven taşır. Ham maksimum zorunlu LOB sonucudur; P0 interpolasyon
kullanmaz. Kalibre saha hatası ancak izinli ve bilinen yönlü testte ölçülebilir.
