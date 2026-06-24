# source: https://github.com/zeittresor
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.offline import plot
from plotly.subplots import make_subplots

from .cad_models import CadRecord, format_number
from .constants import BODY_DISPLAY, BODY_RADIUS_KM
from .simulator import SimulationResult
from .visualization import _html_escape, _theme_palette


def _safe_unit(vec: np.ndarray, fallback: tuple[float, float, float] = (0.0, 1.0, 0.0)) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if not math.isfinite(norm) or norm <= 1e-12:
        return np.array(fallback, dtype=float)
    return np.asarray(vec, dtype=float) / norm


def _split_masked(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.asarray(values, dtype=float).copy()
    out[~mask] = np.nan
    return out


def _select_path(sim: SimulationResult) -> np.ndarray:
    if sim.n_body is not None and getattr(sim.n_body, "size", 0):
        return sim.n_body
    if getattr(sim.two_body, "size", 0):
        return sim.two_body
    return sim.straight


def _select_time_window(times_days: np.ndarray, path: np.ndarray, span_hours: float) -> tuple[np.ndarray, np.ndarray]:
    span_days = max(1.0 / 24.0, float(span_hours) / 24.0)
    mask = np.abs(times_days) <= span_days + 1e-9
    if np.count_nonzero(mask) >= 3:
        return times_days[mask], path[mask]
    # Fallback for coarse simulation steps: keep the nearest samples around closest approach.
    if len(times_days) <= 64:
        return times_days, path
    center = int(np.argmin(np.abs(times_days)))
    lo = max(0, center - 32)
    hi = min(len(times_days), center + 33)
    return times_days[lo:hi], path[lo:hi]


def _surface_basis(path: np.ndarray, radius_km: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    distances = np.linalg.norm(path, axis=1)
    closest_idx = int(np.nanargmin(distances)) if len(distances) else 0
    closest_vec = path[closest_idx] if len(path) else np.array([0.0, 1.0, 0.0])
    up = _safe_unit(closest_vec)
    # Use the closest-approach sub-point as the idealized viewing location.
    observer = up * max(radius_km, 1.0)
    pole = np.array([0.0, 0.0, 1.0], dtype=float)
    east = np.cross(pole, up)
    if np.linalg.norm(east) <= 1e-9:
        east = np.cross(np.array([0.0, 1.0, 0.0], dtype=float), up)
    east = _safe_unit(east, (1.0, 0.0, 0.0))
    north = _safe_unit(np.cross(up, east), (0.0, 1.0, 0.0))
    return observer, up, east, north


def _surface_sky(path: np.ndarray, radius_km: float) -> dict[str, np.ndarray]:
    observer, up, east, north = _surface_basis(path, radius_km)
    rel = path - observer
    rel_dist = np.linalg.norm(rel, axis=1)
    unit = np.array([_safe_unit(v) for v in rel])
    elev = np.degrees(np.arcsin(np.clip(unit @ up, -1.0, 1.0)))
    az = np.degrees(np.arctan2(unit @ east, unit @ north))
    az = (az + 360.0) % 360.0
    sky_r = np.clip(90.0 - elev, 0.0, 180.0)
    return {"az": az, "elev": elev, "sky_r": sky_r, "distance": rel_dist}


def _neo_view(path: np.ndarray, radius_km: float) -> dict[str, np.ndarray]:
    target_vec = -path
    distances = np.linalg.norm(target_vec, axis=1)
    unit = np.array([_safe_unit(v, (-1.0, 0.0, 0.0)) for v in target_vec])
    # Synthetic-body-frame direction. This is not a real camera frame; it is useful for flyby geometry.
    elev = np.degrees(np.arcsin(np.clip(unit[:, 2], -1.0, 1.0)))
    az = (np.degrees(np.arctan2(unit[:, 1], unit[:, 0])) + 360.0) % 360.0
    sky_r = np.clip(90.0 - elev, 0.0, 180.0)
    safe_d = np.maximum(distances, radius_km + 1e-6)
    angular_diameter = 2.0 * np.degrees(np.arcsin(np.clip(radius_km / safe_d, 0.0, 1.0)))
    return {"az": az, "elev": elev, "sky_r": sky_r, "distance": distances, "angular_diameter": angular_diameter}


def _sanitize_name(text: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in text or "object")[:80]


def create_surface_view_html(
    record: CadRecord,
    sim: SimulationResult,
    output_dir: Path,
    viewpoint: str = "surface",
    span_hours: float = 24.0,
    theme_id: str | None = "ocean",
) -> Path:
    """Create a local HTML sky-view approximation for a selected CAD record.

    The view is intentionally derived from the same synthetic target-centered flyby geometry used by
    the 3D visualization. It does not solve a real ground track, light curve, camera pointing, or
    observer ephemeris. It is meant to answer: "what would this approximate flyby look like from the
    target surface or from the flyby object?" while making the approximation explicit.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _sanitize_name(record.designation or record.fullname)
    suffix = "surface" if viewpoint != "neo" else "flyby_object"
    html_path = output_dir / f"cad_surface_view_{safe_name}_{suffix}.html"

    body_code = sim.central_body
    body_name = BODY_DISPLAY.get(body_code, body_code)
    body_radius = BODY_RADIUS_KM.get(body_code, BODY_RADIUS_KM["Earth"])
    full_path = _select_path(sim)
    times_days, path = _select_time_window(sim.times_days, full_path, span_hours)
    times_hours = times_days * 24.0
    palette = _theme_palette(theme_id)

    if viewpoint == "neo":
        data = _neo_view(path, body_radius)
        viewpoint_title = f"View from {record.fullname} toward {body_name}"
        left_title = f"Apparent direction of {body_name} center"
        y1_name = f"{body_name} angular diameter"
        y1_values = data["angular_diameter"]
        y1_title = "Angular diameter (degrees)"
        note = (
            "The observer is placed on the flyby object in the synthetic CAD-derived trajectory. "
            "The polar plot shows the apparent direction of the target-body center in the synthetic flyby frame. "
            "The line plot shows how large the target body would appear as the distance changes."
        )
    else:
        data = _surface_sky(path, body_radius)
        viewpoint_title = f"View from {body_name} surface sub-approach point"
        left_title = f"Sky path of {record.fullname} from idealized surface viewpoint"
        y1_name = "Elevation above horizon"
        y1_values = data["elev"]
        y1_title = "Elevation (degrees)"
        note = (
            "The observer is placed at the idealized sub-approach surface point, directly under the synthetic closest-approach direction. "
            "This is not a real geographic latitude/longitude, not corrected for body rotation, atmosphere, daylight, visibility, magnitude or Horizons ephemerides. "
            "It is a scale-and-geometry viewpoint for the local CAD-derived flyby model."
        )

    distances = np.asarray(data["distance"], dtype=float)
    closest_idx = int(np.nanargmin(distances)) if len(distances) else 0
    visible = data["elev"] >= 0.0
    sky_r_visible = _split_masked(data["sky_r"], visible)
    sky_r_hidden = _split_masked(data["sky_r"], ~visible)

    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "polar"}, {"type": "xy", "secondary_y": True}]],
        subplot_titles=(left_title, "Time profile around closest approach"),
        column_widths=[0.48, 0.52],
        horizontal_spacing=0.12,
    )

    fig.add_trace(
        go.Scatterpolar(
            r=sky_r_visible,
            theta=data["az"],
            mode="lines+markers",
            name="above horizon" if viewpoint != "neo" else "apparent direction",
            marker={"size": 5},
            line={"width": 4, "color": palette["accent"]},
            hovertemplate="t=%{customdata:.2f} h<br>az=%{theta:.1f}°<br>elev=%{text:.1f}°<extra></extra>",
            customdata=times_hours,
            text=data["elev"],
        ),
        row=1,
        col=1,
    )
    if viewpoint != "neo" and np.any(~visible):
        fig.add_trace(
            go.Scatterpolar(
                r=sky_r_hidden,
                theta=data["az"],
                mode="lines+markers",
                name="below horizon",
                marker={"size": 4},
                line={"width": 2, "dash": "dot", "color": palette["muted"]},
                hovertemplate="t=%{customdata:.2f} h<br>az=%{theta:.1f}°<br>elev=%{text:.1f}°<extra></extra>",
                customdata=times_hours,
                text=data["elev"],
            ),
            row=1,
            col=1,
        )

    if len(times_hours):
        fig.add_trace(
            go.Scatterpolar(
                r=[float(data["sky_r"][closest_idx])],
                theta=[float(data["az"][closest_idx])],
                mode="markers+text",
                name="closest approach",
                text=["CA"],
                textposition="top center",
                marker={"size": 11, "symbol": "star", "color": "#ffffff"},
                hovertemplate="closest modeled point<br>t=%{customdata:.2f} h<br>az=%{theta:.1f}°<br>elev=%{text:.1f}°<extra></extra>",
                customdata=[float(times_hours[closest_idx])],
            ),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Scatter(
            x=times_hours,
            y=y1_values,
            mode="lines+markers",
            name=y1_name,
            line={"width": 4, "color": palette["accent"]},
        ),
        row=1,
        col=2,
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=times_hours,
            y=distances,
            mode="lines",
            name="observer-target distance (km)",
            line={"width": 3, "dash": "dash", "color": palette["muted"]},
        ),
        row=1,
        col=2,
        secondary_y=True,
    )

    fig.update_layout(
        title={"text": f"{viewpoint_title}<br><sup>{record.close_approach_date} TDB · {format_number(record.distance_km, 0)} km nominal CAD distance · ±{float(span_hours):g} h shown</sup>", "x": 0.02, "xanchor": "left"},
        paper_bgcolor=palette["panel"],
        plot_bgcolor=palette["panel2"],
        font={"color": palette["text"], "family": "Segoe UI, Arial, sans-serif"},
        height=760,
        margin={"l": 40, "r": 70, "t": 110, "b": 50},
        legend={"orientation": "h", "bgcolor": palette["panel"], "font": {"color": palette["text"]}},
        polar={
            "bgcolor": palette["panel2"],
            "radialaxis": {
                "range": [90, 0],
                "tickvals": [0, 30, 60, 90],
                "ticktext": ["zenith", "60° elev", "30° elev", "horizon"],
                "gridcolor": palette["grid"],
                "linecolor": palette["grid"],
            },
            "angularaxis": {
                "direction": "clockwise",
                "rotation": 90,
                "gridcolor": palette["grid"],
                "linecolor": palette["grid"],
            },
        },
    )
    fig.update_xaxes(title="Hours from modeled closest approach", gridcolor=palette["grid"], zerolinecolor=palette["accent"], row=1, col=2)
    fig.update_yaxes(title=y1_title, gridcolor=palette["grid"], zerolinecolor=palette["accent"], row=1, col=2, secondary_y=False)
    fig.update_yaxes(title="Distance (km)", gridcolor=palette["grid"], row=1, col=2, secondary_y=True)

    div = plot(fig, output_type="div", include_plotlyjs=True, config={"responsive": True, "displaylogo": False})
    title = f"{viewpoint_title} — {record.fullname}"
    explanation = f"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html_escape(title)}</title>
<style>
:root {{ color-scheme: dark; }}
html, body {{ min-height: 100%; }}
body {{ font-family: system-ui, Segoe UI, Arial, sans-serif; margin: 0; background: {palette['bg']}; color: {palette['text']}; }}
.header {{ padding: 18px 24px; background: {palette['panel']}; border-bottom: 1px solid {palette['grid']}; }}
.header h1 {{ margin: 0 0 8px 0; font-size: clamp(1.25rem, 1.8vw, 2.0rem); }}
.header p {{ margin: 0; color: {palette['muted']}; }}
.content {{ padding: 12px 16px 28px 16px; }}
.plot-shell {{ width: min(100%, 1500px); min-height: 580px; margin: 0 auto; background: {palette['panel']}; border: 1px solid {palette['grid']}; border-radius: 10px; overflow: hidden; box-shadow: 0 8px 18px rgba(0,0,0,0.18); }}
.notice {{ width: min(100%, 1500px); margin: 12px auto 0 auto; padding: 10px 14px; background: {palette['notice_bg']}; border: 1px solid {palette['grid']}; border-radius: 8px; color: {palette['muted']}; }}
.notice strong {{ color: {palette['accent']}; }}
</style>
</head>
<body>
<div class="header">
<h1>{_html_escape(title)}</h1>
<p>{_html_escape(body_name)}-centered synthetic viewpoint generated from CAD summary fields.</p>
</div>
<div class="content">
<div class="plot-shell">{div}</div>
<div class="notice"><strong>Viewpoint note:</strong> {_html_escape(note)}</div>
</div>
</body>
</html>
"""
    html_path.write_text(explanation, encoding="utf-8")
    return html_path
