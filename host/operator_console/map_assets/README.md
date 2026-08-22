# Yerel Harita Varlıkları

Bu klasör, operatör konsolunun kendi içinde taşıdığı MapLibre GL JS `5.12.0`
ve PMTiles JS `4.5.0` varlıklarını içerir. İki paket de BSD-3-Clause lisanslıdır;
ilgili lisans metinleri `licenses/` altındadır.

Çevrimiçi harita için kullanıcı, meşru sağlayıcısının MapLibre stil URL'sini
`TEKNOFEST_MAP_STYLE_URL` ortam değişkeniyle verir. Varsayılan çevrimiçi tile
sağlayıcısı yoktur; uygulama kontrolsüz tile indirmez.

Google uydu görünümü yalnız `TEKNOFEST_GOOGLE_MAPS_API_KEY` ortam değişkeni
tanımlandığında etkinleşir. Anahtar repoya yazılmaz.

Çevrimdışı harita için yarışma alanına ait `.pmtiles` arşivini şu yola koyun:

```text
host/operator_console/map_assets/pmtiles/competition.pmtiles
```

Aynı arşivle uyumlu MapLibre stilini şu yola koyun:

```text
host/operator_console/map_assets/styles/competition-style.json
```

Büyük PMTiles arşivi Git'e eklenmez. Şablon, arşiv/stil eşleşmesi için
`styles/competition-style.template.json` altında bulunur. Gerekirse iki yol
`TEKNOFEST_PMTILES_PATH` ve `TEKNOFEST_OFFLINE_STYLE_PATH` ile değiştirilebilir.
