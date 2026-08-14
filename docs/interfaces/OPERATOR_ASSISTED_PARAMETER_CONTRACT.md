# PHASE-04-E1 Operatör Destekli Parametre Sözleşmesi

## Akış

Yalnız `confirmed && observed_this_frame` olay seçilebilir. PHASE-03 candidate bölgesi `[20,4075]` içinde `clamp(max(8, ceil(width/2)), 8, 64)` bin/yan marjla otomatik önizleme üretir. Komşu candidate orta noktası ile dört-bin guard aşılmaz. Otomatik öneri ölçümü başlatmaz; operatör aralığı sürükleyebilir ve sonuç yalnız `Ölçümü Başlat` ile üretilir.

Span `8–512` bindir. Dışında her yanda dört guard ve 32 reference hücresi gerekir; eksik reference için fallback yoktur. Sol/sağ reference farkı `3 dB` üzerindeyse sonuç `uncertain`; dört ardışık frame yoksa `insufficient_quality`; yayın gözlenmiyorsa `not_observed` kullanılır. Span, event, frame, kaynak, profil, Pfa, merkez politikası veya configuration nesli değişince eski sonuç temizlenir.

## Independent-fields-v2 doğrulama protokolü

Otomatik span yalnız ayrı bir kolaylık yeteneğidir; başarısızlığı operatörce çizilen manuel span ölçümlerini kapatmaz. Manuel emisyon merkezi, taşıyıcı çizgisi, OBW99, kalibre edilmemiş güç ve sinyal alanı binding/OOS kararları birbirinden bağımsızdır.

Dört frame, sonlu I/Q/PSD, intent ve generation eşleşmesi, confirmed owner sürekliliği, izole span, reference hücreleri, reference uyumu ve `6 dB` ortak minimum SNR gerçek ortak ön koşullardır. Edge clipping, `%0,5/%99,5` kenarları, temporal kenar kararlılığı ve perturbation robustness yalnız OBW99 alanına aittir. Taşıyıcı çizgisinin gözlenmemesi, OBW99 sonucunun geçersizliği veya sınıflandırmanın Belirsiz kalması diğer alanların sonucunu değiştirmez.

Measurement intent dört frame boyunca aynı event kimliği/revision ve aynı source, pipeline ve configuration nesliyle bağlıdır. Kendi candidate'ı komşu sayılmaz; başka confirmed candidate span ve dört-bin guard ile kesişirse ölçüm `uncertain/neighbor_overlap` olur. Signal ve forced-noise benchmark'ları aynı owner/generation sözleşmesini kullanır. PHASE-03 end-to-end otomatik tespit sonucu manuel parametre capability paydasına katılmaz.

## Matematik

Dört frame ortalama lineer PSD'si `p[k]`, aritmetik ortalama reference noise değeri `n` için:

```text
d[k] = p[k] - n
T = Σ d[k]
```

`T` pozitif ve kanal SNR'si en az `6 dB` değilse ölçüm abstain eder. `d`, toplamı tam `T` olan non-negative simplex üzerine deterministik projekte edilir. Projected `s[k]` sonlu, non-negative ve `Σs=T` olmalıdır. İlk ve son dört hücrenin payı ayrı ayrı en fazla `%0,5` olabilir. OBW99 kenarları `s` kümülatif gücünün `%0,5/%99,5` noktalarıdır; fractional-bin interpolasyon fiziksel FFT çözünürlüğünü artırdığı iddiası değildir.

Yayın merkezi `s` birinci momentidir. Taşıyıcı çizgisi yalnız tepe/noise `≥10 dB`, üç-bin çizgi payı `≥%35` ve dört frame tepe aralığı `≤1 bin` olduğunda log-güç parabolik kestirimdir. Kanal gücü `T·Δf` üzerinden dBFS, tepe gücü PHASE-02 `bin_power_fs2` üzerinden dBFS/bin olur; PHASE-02 normalizasyonu ikinci kez uygulanmaz.

Sinyal alanı dört frame'in her birinde frame-local bant sınırlama ile hesaplanan envelope, iki-seviye, constant-modulus, phase-jump ve instantaneous-frequency özelliklerinden çıkar. Frame sınırları arasında faz farkı alınmaz, raw I/Q geçmişi tutulmaz, çelişkili kanıt `Belirsiz` olur.

## Alan bazlı doğrulama

Capability kimlikleri `emission_center_frequency`, `carrier_line_frequency`, `occupied_bandwidth`, `uncalibrated_power_dbfs` ve `signal_domain` olur. Profil yalnız binding ve OOS'ta geçen alanları içerir. Uygulanabilir olmayan taşıyıcı ailesinde doğru `not_observed` başarısı valid-rate paydasına girmez. Başarısız veya doğrulanmamış alan UI'da sayı göstermez. Otomatik span ayrı convenience capability'sidir.

Kalıcı payload üst sınırı `34.084 byte`, worker/pending sınırı `1/1` ve tek ölçüm okuması en fazla dört adet 4096-kompleks frame'dir. Büyük harici kayıt yalnız `rb/seek/bounded read` ile kullanılır; tam dosya okunmaz veya hashlenmez.
