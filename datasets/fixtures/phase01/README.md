# PHASE-01 Golden Fixture

`known-tone-ci8`, kanonik `ci8` değişim sözleşmesini doğrulayan sentetik ve deterministik SigMF çiftidir. Üçüncü taraf RF kaydı içermez.

Fixture; 8 MS/s, 100 MHz merkez frekansı, 16.384 karmaşık örnek, dört örtüşmesiz çerçeve ve +500 kHz kompleks ton kullanır. Tepe genliği ADR-0002 uyarınca 100 signed count'tur. Beklenen signed FFT bin ve unshifted index `256` değeridir; PHASE-01 FFT çalıştırmaz.

Yeniden üretmek için `python scripts/generate_phase01_fixture.py`, tracked çıktıları yazmadan doğrulamak için `python scripts/generate_phase01_fixture.py --check` çalıştırılır. Data SHA-256/SHA-512 değerleri `results/evidence/phase01/fixture-manifest.json` içindedir.
