"""Configuration-only provider selection for the geographic direction map."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import os
from pathlib import Path
from urllib.parse import urlparse


class MapProviderMode(StrEnum):
    ONLINE_SATELLITE = "ONLINE_SATELLITE"
    ONLINE_MAP = "ONLINE_MAP"
    OFFLINE_MAP = "OFFLINE_MAP"
    FALLBACK_CANVAS = "FALLBACK_CANVAS"


# A public, key-free vector style. It is contacted only after the operator
# opens the map workspace; unavailable networks fall through to the truthful
# offline/canvas state.
DEFAULT_ONLINE_STYLE_URL = "https://tiles.openfreemap.org/styles/liberty"


@dataclass(frozen=True)
class MapProvider:
    mode: MapProviderMode
    label: str
    style_url: str | None = None
    google_maps_api_key: str | None = None


def map_assets_root() -> Path:
    return Path(__file__).resolve().parent / "map_assets"


def _valid_https_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value.strip())
    return value.strip() if parsed.scheme == "https" and parsed.netloc else None


def select_map_providers(
    *,
    environment: dict[str, str] | None = None,
    asset_root: Path | None = None,
) -> tuple[MapProvider, ...]:
    """Return only configured/available providers, ending in the canvas fallback.

    No network request is made here. Runtime JavaScript tries this ordered list
    and falls through if an external style or Google script cannot load.
    """
    env = os.environ if environment is None else environment
    root = map_assets_root() if asset_root is None else asset_root
    providers: list[MapProvider] = []
    google_key = env.get("TEKNOFEST_GOOGLE_MAPS_API_KEY", "").strip()
    if google_key:
        providers.append(MapProvider(MapProviderMode.ONLINE_SATELLITE, "Uydu", google_maps_api_key=google_key))
    style_url = _valid_https_url(env.get("TEKNOFEST_MAP_STYLE_URL", DEFAULT_ONLINE_STYLE_URL))
    if style_url is not None:
        providers.append(MapProvider(MapProviderMode.ONLINE_MAP, "Harita (internet)", style_url=style_url))
    pmtiles_path = Path(env.get("TEKNOFEST_PMTILES_PATH", root / "pmtiles" / "competition.pmtiles"))
    style_path = Path(env.get("TEKNOFEST_OFFLINE_STYLE_PATH", root / "styles" / "competition-style.json"))
    if pmtiles_path.is_file() and style_path.is_file():
        providers.append(MapProvider(MapProviderMode.OFFLINE_MAP, "Çevrimdışı", style_url=style_path.resolve().as_uri()))
    providers.append(MapProvider(MapProviderMode.FALLBACK_CANVAS, "Yedek görünüm"))
    return tuple(providers)
