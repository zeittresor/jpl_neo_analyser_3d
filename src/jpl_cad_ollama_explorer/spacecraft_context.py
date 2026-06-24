# source: https://github.com/zeittresor
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SpacecraftRegion:
    id: str
    body_code: str
    label: str
    min_km: float
    max_km: float
    category: str = "artificial-object region"
    examples: tuple[str, ...] = ()
    note: str = ""

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "SpacecraftRegion":
        return cls(
            id=str(data.get("id", "unknown")),
            body_code=str(data.get("body_code", "")),
            label=str(data.get("label", data.get("id", "unknown"))),
            min_km=float(data.get("min_km", 0.0)),
            max_km=float(data.get("max_km", 0.0)),
            category=str(data.get("category", "artificial-object region")),
            examples=tuple(str(x) for x in data.get("examples", []) if str(x).strip()),
            note=str(data.get("note", "")),
        )

    def overlaps(self, min_distance_km: float, max_distance_km: float) -> bool:
        return max(self.min_km, min_distance_km) <= min(self.max_km, max_distance_km)

    def distance_to_interval(self, min_distance_km: float, max_distance_km: float) -> float:
        if self.overlaps(min_distance_km, max_distance_km):
            return 0.0
        if max_distance_km < self.min_km:
            return self.min_km - max_distance_km
        return min_distance_km - self.max_km


def default_regions() -> list[SpacecraftRegion]:
    # Radial shells are intentionally approximate. They are not ephemerides and do not
    # contain direction, phase, or time-dependent position information. They only let the
    # GUI avoid treating all artificial objects as Earth-orbiting satellites.
    rows: list[dict[str, Any]] = [
        {
            "id": "earth_satellite_operational_shells",
            "body_code": "Earth",
            "label": "Earth LEO/MEO/GEO satellite region",
            "min_km": 6_500,
            "max_km": 50_000,
            "category": "Earth satellite orbit shell",
            "examples": ["LEO satellites", "MEO navigation constellations", "GEO spacecraft"],
            "note": "Approximate geocentric shell containing common Earth satellite regimes.",
        },
        {
            "id": "earth_high_orbit_shell",
            "body_code": "Earth",
            "label": "High Earth orbit / above-GEO region",
            "min_km": 50_000,
            "max_km": 120_000,
            "category": "high Earth orbit shell",
            "examples": ["highly elliptical mission orbits"],
        },
        {
            "id": "earth_cislunar_shell",
            "body_code": "Earth",
            "label": "Cislunar and lunar-distance region",
            "min_km": 120_000,
            "max_km": 470_000,
            "category": "cislunar artificial-object region",
            "examples": ["lunar-transfer spacecraft", "cislunar missions", "Moon-distance assets"],
        },
        {
            "id": "earth_sun_l1_l2_shell",
            "body_code": "Earth",
            "label": "Sun-Earth L1/L2 distance shell",
            "min_km": 1_300_000,
            "max_km": 1_800_000,
            "category": "Lagrange-region shell",
            "examples": ["SOHO/DSCOVR-type L1 missions", "JWST/Gaia-type L2 missions"],
            "note": "Radial shell only; real L1/L2 relevance requires direction and ephemerides.",
        },
        {
            "id": "earth_sun_l4_l5_shell",
            "body_code": "Earth",
            "label": "Sun-Earth L4/L5 distance scale",
            "min_km": 120_000_000,
            "max_km": 180_000_000,
            "category": "Lagrange distance scale",
            "examples": ["Sun-Earth L4/L5 survey concepts"],
            "note": "Very broad radial distance scale; CAD Earth close-approach rows rarely constrain this usefully.",
        },
        {
            "id": "moon_lunar_orbit_shell",
            "body_code": "Moon",
            "label": "Lunar orbit / NRHO mission region",
            "min_km": 1_800,
            "max_km": 90_000,
            "category": "lunar artificial-object region",
            "examples": ["LRO-type low lunar orbiters", "NRHO/Gateway-like mission region"],
        },
        {
            "id": "mars_inner_orbiter_shell",
            "body_code": "Mars",
            "label": "Mars orbiter and moons region",
            "min_km": 3_700,
            "max_km": 80_000,
            "category": "Mars-system artificial-object region",
            "examples": ["Mars orbiters", "Phobos/Deimos-distance operations"],
        },
        {
            "id": "venus_orbiter_shell",
            "body_code": "Venus",
            "label": "Venus orbiter region",
            "min_km": 6_200,
            "max_km": 80_000,
            "category": "Venus artificial-object region",
            "examples": ["Venus orbiter mission shells"],
        },
        {
            "id": "mercury_orbiter_shell",
            "body_code": "Merc",
            "label": "Mercury orbiter region",
            "min_km": 2_500,
            "max_km": 80_000,
            "category": "Mercury artificial-object region",
            "examples": ["Mercury orbiter mission shells"],
        },
        {
            "id": "jupiter_system_shell",
            "body_code": "Juptr",
            "label": "Jupiter spacecraft / major-moon system region",
            "min_km": 75_000,
            "max_km": 2_200_000,
            "category": "Jupiter-system artificial-object region",
            "examples": ["Jupiter orbiters", "Galilean-moon mission regions"],
        },
        {
            "id": "saturn_system_shell",
            "body_code": "Satrn",
            "label": "Saturn spacecraft / major-moon system region",
            "min_km": 65_000,
            "max_km": 1_600_000,
            "category": "Saturn-system artificial-object region",
            "examples": ["Saturn-system mission regions"],
        },
    ]
    return [SpacecraftRegion.from_mapping(row) for row in rows]


def load_regions_with_errors(root_dir: Path) -> tuple[list[SpacecraftRegion], list[str]]:
    """Load the local spacecraft/probe region catalog defensively.

    A user may edit data/spacecraft_regions.json. One malformed entry should not
    disable the whole feature, so invalid rows are skipped and reported while
    the built-in defaults remain available as a fallback.
    """
    path = root_dir / "data" / "spacecraft_regions.json"
    errors: list[str] = []
    if not path.exists():
        return default_regions(), ["Catalog file is missing; using built-in defaults."]
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw.get("regions", raw) if isinstance(raw, dict) else raw
        if not isinstance(items, list):
            return default_regions(), ["Catalog root is not a list or an object with a regions list; using built-in defaults."]
    except Exception as exc:
        return default_regions(), [f"Could not parse catalog JSON: {exc}; using built-in defaults."]

    regions: list[SpacecraftRegion] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"regions[{idx}] is not an object and was skipped.")
            continue
        try:
            region = SpacecraftRegion.from_mapping(item)
            if not region.body_code.strip():
                raise ValueError("body_code is empty")
            if region.max_km <= 0:
                raise ValueError("max_km must be greater than zero")
            if region.min_km < 0:
                raise ValueError("min_km must not be negative")
            if region.max_km < region.min_km:
                # Be forgiving for hand-edited catalogs.
                region = SpacecraftRegion(
                    id=region.id,
                    body_code=region.body_code,
                    label=region.label,
                    min_km=region.max_km,
                    max_km=region.min_km,
                    category=region.category,
                    examples=region.examples,
                    note=(region.note + " ").strip() + "min/max were swapped by loader.",
                )
            regions.append(region)
        except Exception as exc:
            errors.append(f"regions[{idx}] ({item.get('id', 'unknown')!r}) skipped: {exc}")
    if not regions:
        return default_regions(), errors + ["No valid catalog entries remained; using built-in defaults."]
    return regions, errors


def load_regions(root_dir: Path) -> list[SpacecraftRegion]:
    regions, _errors = load_regions_with_errors(root_dir)
    return regions


def save_default_catalog(root_dir: Path) -> None:
    path = root_dir / "data" / "spacecraft_regions.json"
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema": 1,
        "note": "Approximate local radial shells for artificial-space-object context. Not an ephemeris database.",
        "regions": [region.__dict__ | {"examples": list(region.examples)} for region in default_regions()],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
