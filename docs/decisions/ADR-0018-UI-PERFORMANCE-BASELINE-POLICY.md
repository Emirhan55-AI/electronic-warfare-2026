# ADR-0018 — UI Performans Baseline-Regresyon Politikası

## Durum

Kabul edildi. PHASE-06G kapanışındaki tek-koşu UI performans dalgalanması için temiz HEAD ve aday aynı makinede, aynı Python/dependency/display koşullarında beşer kez ölçülmeden politika değiştirilmemiştir.

## Sorun

`test_playback_performance_and_queue_bounds`, 30 FPS hedefli 1,2 saniyelik benchmark'ta tek koşuda en az 20 rendered frame bekliyordu. PHASE-06G source diff'i host/UI kodu içermediği halde temiz aday koşularında 19 ve daha sonra 20–29 gözlenmiştir. İlk beş-koşu median denemesi de isolated hedefli koşuda 25 iken tam unittest yükü altında 18 vermiştir. Tek bir scheduler örneğini veya farklı yük bağlamlarını deterministik işlevsel regresyon gibi değerlendirmek tekrarlanabilir değildir.

## A/B kanıtı

Pre-PHASE-06G HEAD `5eaee83cf192db29e6548fb43ad78d1a01aa7584` detached clean worktree'de 30 FPS rendered frame sonuçları `27, 26, 29, 27, 26`; PHASE-06G adayında `20, 24, 25, 26, 29` olmuştur. Min/median/max baseline için `26/27/29`, aday için `20/25/29` olur. İki dağılım `26..29` aralığında örtüşür; aday hiçbir karakterizasyon koşusunda mevcut 20-frame tabanının altına düşmemiştir. Standart tek-yönlü Mann–Whitney U testi, adayın daha düşük olduğu alternatifinde `p=0,083303697...` verir ve önceden seçilen `alpha=0,05` material-regression kapısını geçmez.

Önceki tek aday koşusunda görülen 19 frame, beş-koşu aday dağılımının ve aynı kaynakların sonraki koşularının değişken olduğunu gösteren recovery tetikleyicisidir; eşik 19'a düşürülmemiştir.

## Karar

İşlevsel unittest kapısı zorunlu kalır. UI benchmark silinmez, skip/xfail yapılmaz ve her tam suite'te çalışır. Test:

- 10 FPS benchmark'ını bir kez,
- 30 FPS benchmark'ını seri beş kez

çalıştırır. Ordinary suite içinde throughput ve heartbeat sayıları görünür benchmark ölçümüdür; koşuların en az bir frame üretmesi gerekir fakat farklı suite yüklerini temiz A/B performans kapısıymış gibi değerlendiren mutlak frame veya scheduler-time eşiği uygulanmaz. Her koşuda waterfall `<=128`, maximum concurrent task `1`, maximum pending intent `<=1` ve stop sonrası active task `0` zorunludur. Bu logical queue/cleanup kriterleri hiçbir koşulda gevşetilmez.

Faz kapanışındaki aynı-makine A/B politika kapısı ayrıca:

1. baseline ve aday için tam beş başarılı koşu,
2. her temiz koşuda heartbeat `<250 ms`, waterfall `<=128`, maximum concurrent task `1`, maximum pending intent `<=1` ve stop sonrası active task `0`,
3. tek-yönlü Mann–Whitney U `p<0,05` **ve** aday medianı baseline medianından düşükse material regression

kurallarını uygular. `alpha=0,05` standart anlamlılık seviyesi sonuçtan sonra ayarlanan frame toleransı değildir. Temiz A/B ölçümü `20 -> 19` veya `20 -> 18` biçiminde yeni bir mutlak eşik üretmez. Raw frame, achieved FPS, heartbeat, queue, waterfall, elapsed time ve exit status kalıcı evidence içinde görünür kalır.

## Sınırlar

Bu politika UI performansını donanım, canlı RF veya sürekli detector throughput kanıtına dönüştürmez. PHASE-06G detector latency ve tek-frame buffer sınırı değişmez. PySide6 uygulama kodu, queue boyutları ve benchmark target/duration değerleri değiştirilmemiştir.
