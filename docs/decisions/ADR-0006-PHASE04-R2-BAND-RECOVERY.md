# ADR-0006 — PHASE-04-R2 Bant Kurtarma Yöntemi

## Durum

Kabul edildi; yalnız kayıtlı ve sentetik I/Q üzerinde doğrulanmak üzere kilitlendi.

## Bağlam

PHASE-04-R1 karşılaştırmasında hiçbir bant tuple'ı bütün bağlayıcı kapıları geçmedi. Aile bazlı teşhis, PHASE-03 bölge parçalanmasının tek kök neden olmadığını; kırpılmış noise ortalamasındaki Hann korelasyon yanlılığı ile ayrık ve sürekli spektral bileşenlere aynı kenar kuralının uygulanmasının birlikte etkili olduğunu gösterdi. Frozen sahne kataloğunun nominal üretici matematiğiyle tutarlı olduğu doğrulandı.

## Karar

R2 için tek upstream zincir şudur:

1. `analysis.clustered-regions-v1`
2. `noise.trimmed-mean-20-hann-calibrated-v1`
3. `band.temporal-morphology-envelope-v1`

Noise düzeltme katsayısı IID üstel varsayımdan alınmaz. Periyodik Hann'ın analitik covariance modeli üzerinde sabit seed ile Monte Carlo kalibrasyonu ve bağımsız gerçek PHASE-02 Hann/FFT kontrolü birlikte geçmeden yöntem kilitlenmez.

Seed ve grow oranları raw PSD üzerinde uygulanır. Bunlar nominal oranlardır; exact Pfa veya CFAR katsayısı değildir. Smoothing yalnız component excess, kenar ve moment hesabında kullanılır.

Salt grow hücrelerinden oluşan bir component, seed hücresi veya gerçek constituent PHASE-03 region desteği yoksa fiziksel zarfa alınmaz ve gap köprüsü olamaz. Çizgisel/geniş ayrımı ENBW karesinden değil, sabit analitik tek-ton ve RRC örneklerinin ikinci moment ayrışmasından türetilir.

İlk public geçerli bant sonucu en az iki ardışık `confirmed AND observed_this_frame` gözlemden sonra üretilir. Ham I/Q veya tam PSD geçmişi tutulmaz. Bant geçmişi `6.528 byte`, bütün parametre geçmişi `74.368 byte` ile sınırlıdır.

## Kanıt ve seçim sınırı

Sabitler `datasets/fixtures/phase04/r2-method-lock.json` içinde binding benchmark öncesinde kilitlenir. Frozen binding benchmark yalnız bir kez çalıştırılır. Sonuçlara göre katsayı, moment eşiği, gap, ground truth, seed veya başarı kapısı değiştirilemez.

Binding sonrasında ayrı seed ailesiyle out-of-sample karakterizasyon yapılır; selector kararına girmez. Harici ISM kaydı annotation taşımadığından bant doğruluğu kanıtı sayılmaz.

## Sonuçlar

Validated PHASE-04 profil yalnız bant, mevcut downstream yöntemler ve birleşik pipeline kapılarının tamamı geçerse oluşturulur. Kısmi profil oluşturulmaz. R2 başarısızsa runtime doğrulanmış PHASE-03 `regional` tespit profiline dönmeye devam eder.

Bu karar dBm, canlı HackRF, FPGA/RTL, saha performansı veya genel modülasyon tanıma iddiası oluşturmaz.
