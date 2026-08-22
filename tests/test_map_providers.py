from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from host.operator_console.map_providers import MapProviderMode, select_map_providers


class MapProviderTests(unittest.TestCase):
    def test_local_map_assets_use_maplibre_and_never_define_a_target_position(self) -> None:
        root = Path(__file__).resolve().parents[1] / "host" / "operator_console" / "map_assets"
        page = (root / "map.html").read_text(encoding="utf-8")
        self.assertIn("./maplibre/maplibre-gl.js", page)
        self.assertIn("Tahmini geliş doğrultusu", page)
        self.assertNotIn("targetPosition", page)
        self.assertNotIn("target_position", page)

    def test_default_online_map_is_key_free_and_never_selects_google(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            providers = select_map_providers(environment={}, asset_root=Path(temporary))
        self.assertEqual(
            (MapProviderMode.ONLINE_MAP, MapProviderMode.FALLBACK_CANVAS),
            tuple(item.mode for item in providers),
        )
        self.assertEqual("Harita (internet)", providers[0].label)

    def test_configured_online_style_is_key_free_map_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            providers = select_map_providers(
                environment={"TEKNOFEST_MAP_STYLE_URL": "https://tiles.example.org/style.json"},
                asset_root=Path(temporary),
            )
        self.assertEqual(
            (MapProviderMode.ONLINE_MAP, MapProviderMode.FALLBACK_CANVAS),
            tuple(item.mode for item in providers),
        )
        self.assertIsNone(providers[0].google_maps_api_key)

    def test_google_key_is_optional_and_never_hard_coded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            providers = select_map_providers(
                environment={"TEKNOFEST_GOOGLE_MAPS_API_KEY": "local-user-key"},
                asset_root=Path(temporary),
            )
        self.assertEqual(MapProviderMode.ONLINE_SATELLITE, providers[0].mode)
        self.assertEqual("local-user-key", providers[0].google_maps_api_key)

    def test_missing_pmtiles_falls_back_but_complete_pair_is_available(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pmtiles").mkdir()
            (root / "styles").mkdir()
            missing = select_map_providers(environment={}, asset_root=root)
            self.assertEqual(
                (MapProviderMode.ONLINE_MAP, MapProviderMode.FALLBACK_CANVAS),
                tuple(item.mode for item in missing),
            )
            (root / "pmtiles" / "competition.pmtiles").write_bytes(b"PMTiles placeholder")
            (root / "styles" / "competition-style.json").write_text("{}", encoding="utf-8")
            present = select_map_providers(environment={}, asset_root=root)
        self.assertEqual(
            (MapProviderMode.ONLINE_MAP, MapProviderMode.OFFLINE_MAP, MapProviderMode.FALLBACK_CANVAS),
            tuple(item.mode for item in present),
        )


if __name__ == "__main__":
    unittest.main()
