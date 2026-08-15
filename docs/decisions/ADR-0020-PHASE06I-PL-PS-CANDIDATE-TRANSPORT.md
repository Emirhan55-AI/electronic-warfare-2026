# ADR-0020 — PHASE-06I PL→PS Aday Transport Sınırı

## Durum

Kabul edildi.

## Faz ve ayrım

Sonraki kontrollü alt-faz **PHASE-06I — PL→PS Aday Paket Transportu ve Sürümlemeli ABI** olur. PHASE-06H'nin sparse candidate stream'i PL'de sürümlemeli packet'a çevrilir. Temporal 2-of-3 association, fiziksel birim dönüşümü, logging ve host delivery Zynq PS sorumluluğudur. PC yalnız display/operator rolündedir.

Authoritative temporal davranış `reference/detection/pipeline.py::DetectionPipeline._update_tracks` içinde yeterince tanımlıdır; fakat mevcut makinede PetaLinux, ARM cross-compiler, sysroot, device-tree/deployment akışı ve kart erişimi yoktur. Bu nedenle temporal C/C++ runtime bu faza zorla katılmaz. ABI için portable C layout/decoder kaynağı hazırlanır; compile/ARM execution iddia edilmez.

## Transport seçimi

Seçilen fiziksel sınır 64-bit AXI4-Stream packetizer → interrupt-driven AXI DMA S2MM → iki bounded PS DDR buffer'dır. DMA IP, PS block design, interrupt controller, device tree ve kernel driver bu fazda instantiate edilmez. Packetizer vendor-independent Icarus simülasyonuyla doğrulanır.

AXI4-Lite polling, frame başına 1352×40 byte'a kadar sparse payload için aşırı CPU/register işlemi gerektirdiğinden reddedilir. Yalnız FIFO, Linux buffer ownership/completion sağlamadığından nihai transport değildir. Unframed DMA ise version, frame identity, count, CRC ve status bütünlük sınırını sağlamaz.

## Backpressure ve frame identity

Packetizer yalnız output DMA stream ready olduğunda ilerler ve `TREADY` ile PHASE-06H'ye kadar backpressure uygular; sessiz drop yoktur. Malformed input açık status bitli packet üretir ve PS bütün packet'ı reddeder. Frame sequence `uint32` olur; reset sonrası sıfırdan başlar ve modulo `2^32` wrap eder. Temporal PS mantığı wall-clock yerine bu sequence'i kullanır.

## Teknik borç

PHASE-06G single-frame'dir, 476131 clock processing latency taşır ve deterministic frame gap gerektirir. Efficient DMA transport continuous live throughput kanıtı değildir. Live HackRF öncesinde ayrı detector-throughput optimization planı zorunlu değerlendirilir.
