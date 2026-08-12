# Uygulama Yol Haritası

Fazlar sıralıdır; bir fazın çıkış kapısı doğrulanmadan ve kullanıcı onayı alınmadan sonraki faza geçilmez.

| Faz | Ad | Çıkış kapısı |
|---|---|---|
| PHASE-00 | Repository ve mühendislik temeli | Repository sözleşmesi, mimari/karar/güvenlik belgeleri, toolchain envanteri ve PHASE-00 doğrulaması başarıyla tamamlanır. |
| PHASE-01 | SigMF girişi sözleşmesi ve deterministik test verisi | SigMF giriş sözleşmesi belgelenir; tekrarlanabilir, etiketli test verileri otomatik olarak doğrulanır. |
| PHASE-02 | Floating-point sinyal tespit referans modeli | KTR 4.1 zincirinin floating-point modeli deterministik testlerde beklenen tespitleri üretir. |
| PHASE-03 | Sabit nokta mimarisi ve hata bütçesi | Sözcük uzunlukları, ölçekleme ve kabul edilebilir model farkları ölçümle onaylanır. |
| PHASE-04 | RTL veri akışı, Hann ve FFT | RTL akış kontrolü, pencereleme ve 4096 FFT çıktıları referans sonuçlarıyla kabul toleransında eşleşir. |
| PHASE-05 | RTL PSD ve üstel ortalama | PSD ve üstel ortalama RTL çıktıları sabit nokta referansıyla kabul toleransında eşleşir. |
| PHASE-06 | OS-CFAR ve aday sinyal birleştirme | Eşikleme ve komşu hücre birleştirme, tanımlı senaryolarda beklenen aday listesini üretir. |
| PHASE-07 | ZedBoard PS/PL entegrasyonu | PS, DDR/AXI DMA ve PL arasındaki kayıtlı veri yolu ZedBoard üzerinde tekrarlanabilir testle doğrulanır. |
| PHASE-08 | PC–ZedBoard kayıtlı veri aktarımı | PC'den Ethernet üzerinden gönderilen kayıtlı I/Q verisi uçtan uca bütünlük ve hız kanıtıyla işlenir. |
| PHASE-09 | HackRF-1 canlı I/Q entegrasyonu | HackRF-1 canlı RX akışı güvenli alma testinde uçtan uca tespit zincirine ulaşır. |
| Sonraki fazlar | Parametre çıkarımı, DF, konum, dinleme ve kontrollü ET | Her görev için ayrı kapsam, güvenlik koşulları ve ölçülebilir kabul kriterleri kullanıcı onayıyla tanımlanır. |

**Mevcut faz: PHASE-00**
