# ADR-0004: Uyarlanabilir Detector ve Doğrulanmış Profil

- Durum: Accepted
- Faz: PHASE-03

## Bağlam

KTR görev sırasını verir, fakat detector türünü veya sayısal eşiği bağlayıcı kılmaz. Bölgesel sağlam taban, CA-CFAR ve OS-CFAR'ın gerçek sistem sözleşmesine uygun sabit sahnelerde tarafsız karşılaştırılması gerekir. Operasyon uygulaması deney kodundan değil, doğrulanmış ve taşınabilir bir profilden çalışmalıdır.

## Karar

Üç yöntem önceden sabitlenmiş yanlış alarm, tespit, geniş bant, temporal ve bounded çalışma kapılarında eşlenik Monte Carlo ile değerlendirilir. Varsayılan Pfa `1e-4` üzerinden önceden tanımlı seçim sırası uygulanır; üç Pfa değeri de doğrulanmış zarfın parçasıdır. Sonuçlara göre sahne, tolerans veya seçim kuralı değiştirilmez.

Tam benchmark sonucunda yalnız bölgesel sağlam taban bütün zorunlu kapıları geçmiştir. Bu nedenle kanonik detector odur. CA-CFAR ve OS-CFAR elenmiştir; tekil bir yöntem bütün kapıları geçtiği için birleşik yöntem değerlendirilmemiştir. Karar dinamik süreye veya makine kimliğine dayanmaz.

Operasyon zinciri allowlist blok registry'si ve `validated` profilden kurulur. Tam görsel node editor, kullanıcı kodu/plugin, otomatik HDL, parametre çıkarımı, canlı HackRF, RTL/ZedBoard ve TX bu kararın kapsamında değildir.

## Sonuçlar

Kanonik yöntem kanıt değişirse kontrollü yeniden tesis edilebilir; profil sessizce üzerine yazılmaz. Floating-point referans seçim, ilerideki FPGA uygulamasını otomatik tanımlamaz. Her PL bloğu için sabit nokta, gecikme ve kaynak doğrulaması ayrıca gerekir.
