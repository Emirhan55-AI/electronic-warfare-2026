# P0 PC→ZedBoard IQ Taşıma Sözleşmesi

Her TCP yükü 44-byte little-endian header ve bounded `ci8` payload taşır. Header;
magic `P0IQ`, sürüm, örnek biçimi, header boyu, uint32 sıra numarası, uint32 frame
kimliği, chunk indisi/adedi, uint64 merkez frekansı, örnekleme hızı, karmaşık örnek
adedi, payload uzunluğu ve payload CRC32 alanlarından oluşur.

Bir frame tek chunk olabilir veya aynı `frame_id` ile 1–65535 chunk'a ayrılabilir.
`chunk_index` sıfır tabanlıdır. Payload en fazla 131.072 byte ve tam I/Q çiftidir.
Sıra/CRC/uzunluk/chunk hataları allowlist hata kodlarıyla fail-closed raporlanır.

`LoopbackIQTransport`, gerçek codec ve bounded thread-safe queue ile yerel emulator
kanıtıdır. `TCPClientIQTransport` yalnız Bilgisayar-1 istemcisidir; repository'de
ZedBoard sunucusu varmış gibi davranmaz. Bağlantı durumu `DISCONNECTED`,
`CONNECTED` veya `ERROR`; gönderilen/alınan frame/byte, CRC, sıra ve queue-drop
istatistikleri bounded sonuç nesnesindedir.

Bu sözleşme ağ throughput, PetaLinux server, DMA driver veya ZedBoard çalışması
kanıtı değildir.
