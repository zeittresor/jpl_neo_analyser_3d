# source: https://github.com/zeittresor
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .constants import AU_KM, BODY_DISPLAY, LD_KM


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        text = str(value).strip()
        if not text:
            return None
        if text.startswith("<"):
            text = text.replace("<", "").strip()
        return float(text)
    except Exception:
        return None


def diameter_from_h(h: float, albedo: float = 0.14) -> float:
    # D(km) = 1329 / sqrt(p) * 10^(-H/5)
    return 1329.0 / (albedo ** 0.5) * (10.0 ** (-h / 5.0))


@dataclass(slots=True)
class CadRecord:
    raw: dict[str, Any]
    query_body: str = "Earth"

    @classmethod
    def from_fields(cls, fields: list[str], row: list[Any], query_body: str = "Earth") -> "CadRecord":
        values = {field: row[idx] if idx < len(row) else None for idx, field in enumerate(fields)}
        return cls(values, query_body=query_body)

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)

    @property
    def designation(self) -> str:
        return str(self.get("des", "")).strip()

    @property
    def fullname(self) -> str:
        value = self.get("fullname")
        return str(value).strip() if value else self.designation

    @property
    def body_code(self) -> str:
        body = self.get("body") or self.query_body or "Earth"
        return str(body)

    @property
    def body_name(self) -> str:
        return BODY_DISPLAY.get(self.body_code, self.body_code)

    @property
    def close_approach_date(self) -> str:
        return str(self.get("cd", "")).strip()

    @property
    def jd(self) -> float | None:
        return _float_or_none(self.get("jd"))

    @property
    def dist_au(self) -> float | None:
        return _float_or_none(self.get("dist"))

    @property
    def dist_min_au(self) -> float | None:
        return _float_or_none(self.get("dist_min"))

    @property
    def dist_max_au(self) -> float | None:
        return _float_or_none(self.get("dist_max"))

    @property
    def v_rel_kms(self) -> float | None:
        return _float_or_none(self.get("v_rel"))

    @property
    def v_inf_kms(self) -> float | None:
        return _float_or_none(self.get("v_inf"))

    @property
    def h_mag(self) -> float | None:
        return _float_or_none(self.get("h"))

    @property
    def diameter_km(self) -> float | None:
        return _float_or_none(self.get("diameter"))

    @property
    def diameter_sigma_km(self) -> float | None:
        return _float_or_none(self.get("diameter_sigma"))

    @property
    def distance_km(self) -> float | None:
        return self.dist_au * AU_KM if self.dist_au is not None else None

    @property
    def distance_ld(self) -> float | None:
        return self.distance_km / LD_KM if self.distance_km is not None else None

    @property
    def min_distance_ld(self) -> float | None:
        return (self.dist_min_au * AU_KM / LD_KM) if self.dist_min_au is not None else None

    @property
    def max_distance_ld(self) -> float | None:
        return (self.dist_max_au * AU_KM / LD_KM) if self.dist_max_au is not None else None

    def estimated_diameter_range_km(self) -> tuple[float | None, float | None, float | None]:
        if self.diameter_km is not None:
            sigma = self.diameter_sigma_km or 0.0
            return max(0.0, self.diameter_km - sigma), self.diameter_km, self.diameter_km + sigma
        if self.h_mag is None:
            return None, None, None
        # Albedo uncertainty dominates if no direct diameter is known.
        low = diameter_from_h(self.h_mag, 0.25)
        nominal = diameter_from_h(self.h_mag, 0.14)
        high = diameter_from_h(self.h_mag, 0.05)
        return low, nominal, high

    def risk_bucket(self) -> tuple[str, str]:
        """Human-readable triage bucket, not an official risk category."""
        min_ld = self.min_distance_ld or self.distance_ld
        _, nominal_d, high_d = self.estimated_diameter_range_km()
        v = self.v_rel_kms or 0.0
        if min_ld is None:
            return "Unknown", "No distance value is available."
        size_m = (nominal_d or high_d or 0.0) * 1000.0
        if min_ld < 1.0:
            if size_m >= 140:
                return "Very close + large", "Closer than the Moon and size estimate is potentially substantial. Treat as high-attention data and verify with official JPL/CNEOS pages."
            return "Very close", "Closer than the Moon. Small objects can still be scientifically important even if not globally hazardous."
        if min_ld < 5.0:
            if size_m >= 140 or v >= 25.0:
                return "Close / high attention", "Within five lunar distances and either potentially large or fast."
            return "Close", "Within five lunar distances."
        if min_ld < 20.0:
            return "Nearby", "Astronomically nearby, but not unusually close for CAD queries."
        return "Routine", "Farther than twenty lunar distances in this filtered dataset."

    def summary_lines(self) -> list[str]:
        low_d, nominal_d, high_d = self.estimated_diameter_range_km()
        bucket, explanation = self.risk_bucket()
        lines = [
            f"Object: {self.fullname}",
            f"Approach body: {self.body_name}",
            f"Close approach time (TDB): {self.close_approach_date}",
            f"Nominal distance: {format_number(self.dist_au, 8)} au / {format_number(self.distance_ld, 2)} LD / {format_number(self.distance_km, 0)} km",
            f"3-sigma distance range: {format_number(self.min_distance_ld, 2)} to {format_number(self.max_distance_ld, 2)} LD",
            f"Relative speed: {format_number(self.v_rel_kms, 2)} km/s; v-infinity: {format_number(self.v_inf_kms, 2)} km/s",
            f"Time uncertainty: {self.get('t_sigma_f', 'n/a')}",
            f"Absolute magnitude H: {format_number(self.h_mag, 2)}",
            f"Diameter: {format_diameter(low_d, nominal_d, high_d, self.diameter_km is not None)}",
            f"Local triage: {bucket} — {explanation}",
        ]
        return lines

    def table_values(self) -> dict[str, str]:
        bucket, _ = self.risk_bucket()
        low_d, nominal_d, high_d = self.estimated_diameter_range_km()
        diameter_text = format_diameter(low_d, nominal_d, high_d, self.diameter_km is not None)
        return {
            "Object": self.fullname,
            "Date TDB": self.close_approach_date,
            "Body": self.body_name,
            "Distance LD": format_number(self.distance_ld, 3),
            "Min LD": format_number(self.min_distance_ld, 3),
            "Max LD": format_number(self.max_distance_ld, 3),
            "Distance km": format_number(self.distance_km, 0),
            "v_rel km/s": format_number(self.v_rel_kms, 2),
            "H": format_number(self.h_mag, 2),
            "Diameter": diameter_text,
            "Uncertainty": str(self.get("t_sigma_f", "")),
            "Triage": bucket,
        }


def format_number(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "n/a"
    if decimals <= 0:
        return f"{value:,.0f}"
    return f"{value:,.{decimals}f}"


def format_diameter(low: float | None, nominal: float | None, high: float | None, measured: bool) -> str:
    if nominal is None:
        return "n/a"
    if measured:
        if low is not None and high is not None and high > low:
            return f"{nominal * 1000:,.0f} m measured (± approx.)"
        return f"{nominal * 1000:,.0f} m measured"
    if low is not None and high is not None:
        return f"~{nominal * 1000:,.0f} m est. ({low * 1000:,.0f}-{high * 1000:,.0f} m)"
    return f"~{nominal * 1000:,.0f} m est."


def parse_cad_payload(payload: dict[str, Any], query_body: str = "Earth") -> list[CadRecord]:
    fields = payload.get("fields") or []
    data = payload.get("data") or []
    if not isinstance(fields, list) or not isinstance(data, list):
        return []
    return [CadRecord.from_fields(fields, row, query_body=query_body) for row in data if isinstance(row, list)]
