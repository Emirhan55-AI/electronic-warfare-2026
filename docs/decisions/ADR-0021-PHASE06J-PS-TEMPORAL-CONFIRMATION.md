# ADR-0021: PHASE-06J PS temporal aday doğrulama sınırı

## Durum

Kabul edildi.

## Karar

PHASE-06J, PHASE-06I ABI v1 packet'larını tüketen platformdan bağımsız C11 çekirdeğinde PHASE-03 `DetectionPipeline._update_tracks` davranışını uygular. Çekirdek Zynq PS/ARM runtime için hedeflenir; geliştirme makinesindeki derleme ve Python golden eşdeğerliği hedef mimariyi değiştirmez ve PC'yi runtime algoritma motoru yapmaz.

Temporal sözleşme 3 frame'lik track geçmişinde en az 2 gözlem, önceki inclusive span'ın iki bin genişletilmesiyle pozitif-overlap association, global deterministik greedy tie sırası, iki ardışık miss ile expiry, 64 aktif track ve 128 ended-history sınırıdır. PHASE-06I `uint32` frame ID'si kullanılır; `FFFFFFFF→00000000` ardışık, diğer gap'ler state reset nedenidir. Status-marked veya malformed packet state'i değiştirmeden reddedilir.

Yeni PL RTL eklenmez. Gerçek AXI DMA, PetaLinux driver/device tree, ARM cross-build ve ZedBoard execution ayrı entegrasyon kapısıdır. Fiziksel Hz dönüşümü bu faza birleştirilmez; RF center frequency ve sample rate packet ABI'sında değildir. Coarse span hassas/occupied bandwidth değildir; dBFS/dBm için normalization veya calibration sözleşmesi yoktur.

## Sonuçlar

C çekirdeği host ve ARM derleyicilerinde ortak kaynak olarak kalır; Linux/DMA glue matematiksel state machine'den ayrılır. Host C11 derleme ve Python↔C exact semantic karşılaştırması PHASE-06J'yi kapatabilir; ARM veya kart sonucu yalnız gerçekten çalıştırılırsa ayrıca iddia edilebilir. PHASE-06G'nin 476131-clock frame-gap borcu değişmeden taşınır.
