# Operatör Arayüzü Referans Araştırma Kapsamı

- Hazırlık tarihi: 2026-08-22
- Uygulama paketi: APP-E ön araştırması
- Durum: Tasarım kararı değildir; uygulanacak örüntü adaylarıdır

## İlke

Referans uygulamaların görsel kabuğu kopyalanmayacaktır. Her örüntü KTR görev
akışına, gerçek donanım sınırlarına ve operatörün karar süresine göre yeniden
değerlendirilecektir.

Hedef demo ekranı değil yayın adayı üründür. Tasarım kararı; kurulum, paketleme,
gerçek kaynak bağlantısı, hata kurtarma, minimum ekran kullanımı ve uzun süreli
operasyon kararlılığıyla birlikte verilecektir.

## Referanslar ve alınacak örüntüler

| Referans | Güçlü örüntü | Projeye uyarlama | Alınmayacak taraf |
|---|---|---|---|
| GNU Radio Companion | Kaynak→işleme→sonuç blok akışı, port/veri türü görünürlüğü, yeniden kullanılabilir bloklar | Sistem ekranında salt okunur `Kaynak → Ön İşleme → FFT → Tespit → Parametre` sağlık akışı; her blok gerçek runtime durumu ve sahibiyle gösterilir | Operatörün çalışma zamanında DSP grafiğini serbestçe değiştirmesi |
| GNU Radio QT GUI sink'leri | Frekans, waterfall ve zaman alanını ayrı ölçüm görünümü olarak sunma | Spektrum/spektrogramı tek merkez çalışma alanında tutma; görünüm ayarlarını ikincil panelde toplama | Aynı anda gereksiz çok sayıda sink/pencere açma |
| SDR++ | Üst barda yalnız sık kullanılan kaynak, başlat/durdur, frekans ve seviye; merkezde FFT/waterfall | Operasyon ekranında tek birincil eylem ve seçili sinyal bağlamı | Genel amaçlı VFO/radyo kontrollerini KTR dışı çoğaltma |
| SDRangel | Device, spectrum, channel ve feature ayrımı; çoklu workspace ve dock düzeni | `Operasyon`, `Yön Bulma`, `Sistem` çalışma alanları ve gerekirse ikinci ekran düzeni | Varsayılan görünümde serbest MDI karmaşıklığı |
| u-center | Bağlantı, loglama ve GNSS analiz görünümlerinin ayrı görev bağlamları | Kaynak bağlantı durumu, kayıt/replay kimliği ve sensör doğruluğunu sürekli ama sakin biçimde gösterme | KTR'de bulunmayan GNSS ölçümlerini göstermelik ekleme |
| KrakenSDR | DoA, harita ve veri toplama durumunun birlikte ele alınması | Yön ölçümü, sensör konumu, referans yönü ve LOB kaynağını aynı çalışma alanında birleştirme | Faz uyumlu çok kanal/MUSIC sonucu varmış gibi gösterme |
| Qt Quick/Qt Design Studio | Durum tabanlı geçişler, bileşenleşme ve GPU destekli sahne grafiği | APP-E'de aynı ViewModel ile ölçülecek modern arayüz prototipi | Ölçülmeden tam teknoloji geçişi kararı verme |

## Önerilen blok akışı görünümü

Operatör ekranında grafik düzenlenebilir olmayacaktır. Salt okunur çalışma zamanı
akışı aşağıdaki anlamı taşır:

```text
[Veri Kaynağı]
      │ iq.frame/v1
      ▼
[Ön İşleme] ──► [FFT / Güç] ──► [OS-CFAR] ──► [Aday Birleştirme]
                                                   │
                                                   ▼
                                      [Zamansal Doğrulama]
                                                   │
                              ┌────────────────────┴───────────────┐
                              ▼                                    ▼
                     [Parametre Çıkarımı]                  [Operatör Seçimi]
                              │                                    │
                              └──────────────► [Dinleme / DF] ◄────┘
```

Her blok yalnız şu dört durumdan birini gösterir:

- `KULLANILMIYOR`
- `HAZIR`
- `ÇALIŞIYOR`
- `HATA`

`DOĞRULANMADI`, `DONANIM YOK` veya `REPLAY` gibi kaynak niteliği ayrı rozet olarak
gösterilir; başarı durumu gibi sunulmaz.

## Bilgi mimarisi adayı

1. **Operasyon:** Kaynak, spektrum/spektrogram, tespitler ve seçili sinyal.
2. **Yön Bulma (DF):** Anten yönelimi, açı–güç ölçümü, sensör konumu ve harita.
3. **Sistem:** Blok akışı, HackRF/ZedBoard/FPGA/taşıma sağlığı ve kayıt günlüğü.
4. **Laboratuvar:** Replay, eğitim ve TX-kilitli offline doğrulama; yayın paketinden
   ayrı mühendislik giriş noktası.

## Kaynaklar

- GNU Radio QT GUI: <https://www.gnuradio.org/doc/doxygen/page_qtgui.html>
- GNU Radio Companion: <https://wiki.gnuradio.org/index.php?title=GNU_Radio_Companion>
- SDR++ ana proje ve modülerlik: <https://github.com/AlexandreRouma/SDRPlusPlus>
- SDR++ arayüz kılavuzu: <https://github.com/AlexandreRouma/SDRPlusPlus/wiki/Manual>
- SDRangel çalışma alanları: <https://github.com/f4exb/sdrangel/wiki/Quick-start>
- SDRangel spektrum bileşeni: <https://github.com/f4exb/sdrangel/blob/master/sdrgui/gui/spectrum.md>
- u-center kullanıcı kılavuzu: <https://content.u-blox.com/sites/default/files/u-center_Userguide_UBX-13005250.pdf>
- KrakenSDR DoA: <https://github.com/krakenrf/krakensdr_doa>
- Qt Quick en iyi uygulamalar: <https://doc.qt.io/qt-6/qtquick-bestpractices.html>
- Qt Quick performans: <https://doc.qt.io/qt-6/qtquick-performance.html>
