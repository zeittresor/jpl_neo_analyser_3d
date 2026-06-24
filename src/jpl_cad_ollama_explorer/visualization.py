# source: https://github.com/zeittresor
from __future__ import annotations

import math
import webbrowser
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.offline import plot

from .cad_models import CadRecord, format_number
from .constants import BODY_DISPLAY, BODY_RADIUS_KM
from .simulator import SimulationResult


ROCKY_BODIES = {"Merc", "Venus", "Earth", "Moon", "Mars", "Pluto"}
GAS_GIANTS = {"Juptr", "Satrn", "Urnus", "Neptn"}
ICEY_BODY_NAMES = {"comet", "ice", "icy"}


def _normalized_noise(uu: np.ndarray, vv: np.ndarray) -> np.ndarray:
    noise = (
        0.52 * np.sin(uu * 3.0 + vv * 1.2)
        + 0.28 * np.cos(uu * 7.0 - vv * 2.6)
        + 0.17 * np.sin(uu * 13.0 + vv * 5.4)
        + 0.09 * np.cos(uu * 19.0 - vv * 11.0)
    )
    mn = float(np.min(noise))
    mx = float(np.max(noise))
    if mx - mn < 1e-9:
        return np.zeros_like(noise)
    return (noise - mn) / (mx - mn)


def _body_colorscale(body_code: str, object_role: str = "body") -> list[list[object]]:
    if object_role == "flyby":
        return [
            [0.0, "#2d2d2d"],
            [0.25, "#58524a"],
            [0.5, "#8f7f6a"],
            [0.75, "#b39978"],
            [1.0, "#d9c9b5"],
        ]
    if body_code == "Earth":
        return [
            [0.0, "#012846"],
            [0.22, "#035a8b"],
            [0.43, "#2c7fb8"],
            [0.44, "#d6c19a"],
            [0.52, "#3f8f44"],
            [0.7, "#6d8f47"],
            [0.84, "#8d7a5a"],
            [0.95, "#e7eef7"],
            [1.0, "#ffffff"],
        ]
    if body_code == "Moon":
        return [[0.0, "#2a2a2d"], [0.45, "#66666d"], [0.7, "#94949c"], [1.0, "#d6d6dc"]]
    if body_code == "Merc":
        return [[0.0, "#2b2522"], [0.4, "#705f53"], [0.75, "#a18f7f"], [1.0, "#d1c3b8"]]
    if body_code == "Venus":
        return [[0.0, "#4a3218"], [0.25, "#865c2d"], [0.55, "#b88a51"], [0.78, "#e0c596"], [1.0, "#fff2cf"]]
    if body_code == "Mars":
        return [[0.0, "#3b1810"], [0.22, "#7d3020"], [0.55, "#b44b30"], [0.8, "#d67d57"], [1.0, "#fff0e5"]]
    if body_code == "Juptr":
        return [[0.0, "#70543d"], [0.18, "#b08a6a"], [0.42, "#d8bc93"], [0.64, "#b78057"], [0.82, "#e8d5bc"], [1.0, "#f3e8d8"]]
    if body_code == "Satrn":
        return [[0.0, "#675847"], [0.2, "#b59b72"], [0.45, "#d7c39d"], [0.7, "#c2ad87"], [1.0, "#f1e4c8"]]
    if body_code == "Urnus":
        return [[0.0, "#246d80"], [0.3, "#52a9b5"], [0.65, "#91d6d9"], [1.0, "#d9ffff"]]
    if body_code == "Neptn":
        return [[0.0, "#0c275c"], [0.28, "#224a9f"], [0.65, "#4e78d1"], [1.0, "#b8d3ff"]]
    if body_code == "Pluto":
        return [[0.0, "#4a3a31"], [0.35, "#8b705a"], [0.7, "#d0b59a"], [1.0, "#f6efe6"]]
    return [[0.0, "#164d5c"], [0.5, "#2b8ca6"], [1.0, "#c3f0ff"]]


def _surface_texture_map(body_code: str, uu: np.ndarray, vv: np.ndarray, texture_mode: str, object_role: str = "body") -> tuple[np.ndarray, list[list[object]]]:
    if texture_mode == "off":
        return np.ones_like(uu) * 0.6, _body_colorscale(body_code, object_role)

    lat = np.cos(vv)
    lon = uu
    noise = _normalized_noise(uu, vv)

    if object_role == "flyby":
        # Generic rocky small-body appearance.
        craters = (np.sin(lon * 9.0) * np.cos(vv * 8.0) + np.sin(lon * 17.0 + vv * 5.5)) * 0.08
        values = np.clip(0.18 + 0.72 * noise + craters, 0.0, 1.0)
        return values, _body_colorscale(body_code, object_role)

    if body_code == "Earth":
        continents = (
            0.45 * np.sin(lon * 2.3)
            + 0.35 * np.cos(vv * 3.8)
            + 0.2 * np.sin(lon * 6.2 + vv * 3.0)
            + 0.12 * np.cos(lon * 10.5 - vv * 4.0)
        )
        land_mask = continents + (noise - 0.5) * 0.35 > 0.18
        values = np.where(land_mask, 0.56 + 0.2 * noise, 0.08 + 0.22 * noise)
        # beaches
        coast_mask = np.abs(continents - 0.18) < 0.06
        values = np.where(coast_mask, 0.44 + 0.02 * noise, values)
        # polar caps and a few cloud streaks
        poles = np.abs(lat) > 0.9
        clouds = (np.sin(lon * 11.0 + vv * 5.0) + np.cos(lon * 7.0 - vv * 7.5)) > 1.25
        values = np.where(clouds, np.maximum(values, 0.93), values)
        values = np.where(poles, 0.96, values)
        return np.clip(values, 0.0, 1.0), _body_colorscale(body_code)

    if body_code in {"Moon", "Merc"}:
        maria = 0.35 + 0.45 * noise
        crater_rims = (np.sin(lon * 14.0) * np.sin(vv * 9.5)) * 0.08
        return np.clip(maria + crater_rims, 0.0, 1.0), _body_colorscale(body_code)

    if body_code == "Venus":
        swirls = 0.42 + 0.35 * np.sin(vv * 4.0 + lon * 2.5) + 0.18 * np.cos(lon * 9.0 - vv * 2.0)
        return np.clip((swirls + 1.0) / 2.0, 0.0, 1.0), _body_colorscale(body_code)

    if body_code == "Mars":
        values = 0.3 + 0.45 * noise + 0.1 * np.sin(lon * 8.0)
        values = np.where(np.abs(lat) > 0.88, 0.94, values)
        return np.clip(values, 0.0, 1.0), _body_colorscale(body_code)

    if body_code in GAS_GIANTS:
        base = 0.5 + 0.32 * np.sin(vv * 10.0) + 0.12 * np.sin(vv * 24.0 + lon * 1.2)
        if body_code == "Juptr":
            storm = np.exp(-(((lon - 4.7) % (2 * math.pi)) - math.pi) ** 2 / 0.18) * np.exp(-(lat + 0.25) ** 2 / 0.02)
            base += storm * 0.24
        return np.clip(base, 0.0, 1.0), _body_colorscale(body_code)

    if body_code == "Pluto":
        values = 0.3 + 0.5 * noise
        heart = np.exp(-((lat - 0.15) ** 2 / 0.08 + (((lon - 1.7) % (2 * math.pi)) - math.pi) ** 2 / 0.35))
        values = np.clip(values + heart * 0.35, 0.0, 1.0)
        return values, _body_colorscale(body_code)

    return 0.2 + 0.7 * noise, _body_colorscale(body_code)


def _sphere_mesh(radius: float, scale: float = 1.0, n: int = 72, body_code: str = "Earth", texture_mode: str = "off", object_role: str = "body") -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[list[object]]]:
    u = np.linspace(0, 2 * math.pi, n)
    v = np.linspace(0, math.pi, max(20, n // 2))
    uu, vv = np.meshgrid(u, v, indexing="ij")
    rr = np.ones_like(uu) * radius * scale

    if texture_mode in {"simple", "enhanced"}:
        noise = _normalized_noise(uu, vv)
        if object_role == "flyby":
            amp = 0.12 if texture_mode == "simple" else 0.25
            rr *= 1.0 + (noise - 0.5) * amp
        elif body_code in ROCKY_BODIES:
            amp = 0.006 if texture_mode == "simple" else 0.015
            rr *= 1.0 + (noise - 0.5) * amp
        elif body_code in GAS_GIANTS and texture_mode == "enhanced":
            rr *= 1.0 + 0.004 * np.sin(vv * 24.0)

    x = rr * np.cos(uu) * np.sin(vv)
    y = rr * np.sin(uu) * np.sin(vv)
    z = rr * np.cos(vv)
    surfacecolor, colorscale = _surface_texture_map(body_code, uu, vv, texture_mode, object_role)
    return x, y, z, surfacecolor, colorscale


def _add_path(fig: go.Figure, path: np.ndarray, name: str, width: int = 4, dash: str | None = None) -> None:
    fig.add_trace(
        go.Scatter3d(
            x=path[:, 0],
            y=path[:, 1],
            z=path[:, 2],
            mode="lines",
            name=name,
            line={"width": width, **({"dash": dash} if dash else {})},
        )
    )


def _add_textured_body(
    fig: go.Figure,
    center: tuple[float, float, float],
    radius_km: float,
    scale: float,
    body_code: str,
    texture_mode: str,
    name: str,
    opacity: float = 1.0,
    object_role: str = "body",
    resolution: int = 72,
) -> None:
    x, y, z, surfacecolor, colorscale = _sphere_mesh(
        radius_km,
        scale=scale,
        n=resolution,
        body_code=body_code,
        texture_mode=texture_mode,
        object_role=object_role,
    )
    fig.add_trace(
        go.Surface(
            x=x + center[0],
            y=y + center[1],
            z=z + center[2],
            surfacecolor=surfacecolor,
            colorscale=colorscale,
            cmin=0,
            cmax=1,
            opacity=opacity,
            showscale=False,
            name=name,
            hovertemplate=f"{name}<extra></extra>",
            lighting={"ambient": 0.55, "diffuse": 0.75, "specular": 0.15, "roughness": 0.8, "fresnel": 0.04},
            contours={"x": {"show": False}, "y": {"show": False}, "z": {"show": False}},
        )
    )



def _html_escape(text: str) -> str:
    import html as _html

    return _html.escape(str(text), quote=True)


# theme palette kept compact for generated HTML.
def _theme_palette(theme_id: str | None) -> dict[str, str]:
    palettes = {
        "ocean": {
            "bg": "#071820", "panel": "#0d2633", "panel2": "#061219", "text": "#e2f6ff",
            "muted": "#a8cfdd", "accent": "#00a7c7", "grid": "#1d5a73", "notice_bg": "#102c39",
        },
        "dark": {
            "bg": "#10131a", "panel": "#171b24", "panel2": "#11151d", "text": "#e6e6e6",
            "muted": "#b9c1d3", "accent": "#5aa0ff", "grid": "#333b4c", "notice_bg": "#1b2230",
        },
        "aurora": {
            "bg": "#07101c", "panel": "#0d1728", "panel2": "#080a18", "text": "#ecf7ff",
            "muted": "#c7b8ff", "accent": "#b277ff", "grid": "#3a7a8c", "notice_bg": "#151239",
        },
        "matrix": {
            "bg": "#020602", "panel": "#061206", "panel2": "#020a02", "text": "#d8ffd8",
            "muted": "#94d694", "accent": "#39ff14", "grid": "#1f6f27", "notice_bg": "#071407",
        },
        "sepia": {
            "bg": "#251d13", "panel": "#34291b", "panel2": "#21180f", "text": "#fff1d0",
            "muted": "#d9c29a", "accent": "#d79a45", "grid": "#7b5c33", "notice_bg": "#3b2d1c",
        },
        "hellfire": {
            "bg": "#170505", "panel": "#2a0909", "panel2": "#150303", "text": "#ffe8d7",
            "muted": "#ffb391", "accent": "#ff5a1f", "grid": "#7a2014", "notice_bg": "#2d1008",
        },
        "purple": {
            "bg": "#12091e", "panel": "#211034", "panel2": "#100718", "text": "#f0e8ff",
            "muted": "#ccb8ef", "accent": "#b277ff", "grid": "#57317a", "notice_bg": "#26133d",
        },
        "light": {
            "bg": "#f5f7fb", "panel": "#ffffff", "panel2": "#eef3f9", "text": "#1b2430",
            "muted": "#4a5d70", "accent": "#006ea8", "grid": "#c7d4e0", "notice_bg": "#eef6fb",
        },
    }
    return palettes.get(str(theme_id or "ocean"), palettes["ocean"])


def _flyby_visual_radius_km(record: CadRecord, body_radius: float, target_scale: float) -> float:
    if record.diameter_km is not None and record.diameter_km > 0:
        base = max(record.diameter_km / 2.0, 0.01)
    else:
        base = max(body_radius * 0.0002, 0.01)
    # Strong visual exaggeration so the object remains visible in a large-scale view.
    return max(base * 4000.0, body_radius * target_scale * 0.025)


def create_visualization_html(
    record: CadRecord,
    sim: SimulationResult,
    output_dir: Path,
    target_scale: float = 20.0,
    show_disclaimer: bool = False,
    theme_id: str | None = "ocean",
    texture_mode: str = "off",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(ch if ch.isalnum() else "_" for ch in record.designation or "object")[:80]
    html_path = output_dir / f"cad_visualization_{safe_name}.html"

    central = sim.central_body
    body_name = BODY_DISPLAY.get(central, central)
    body_radius = BODY_RADIUS_KM.get(central, BODY_RADIUS_KM["Earth"])
    palette = _theme_palette(theme_id)

    fig = go.Figure()
    _add_textured_body(
        fig,
        center=(0.0, 0.0, 0.0),
        radius_km=body_radius,
        scale=target_scale,
        body_code=central,
        texture_mode=texture_mode,
        name=f"{body_name} (scaled {target_scale:g}x)",
        opacity=0.98,
        object_role="body",
        resolution=84 if texture_mode == "enhanced" else 64,
    )

    _add_path(fig, sim.straight, "Straight-line CAD geometry", width=3, dash="dash")
    _add_path(fig, sim.two_body, f"{body_name} gravity only", width=5)
    if sim.n_body is not None:
        _add_path(fig, sim.n_body, "Approx. Sun + planet tidal perturbations", width=4)

    distances = np.linalg.norm(sim.two_body, axis=1)
    closest_idx = int(np.argmin(distances)) if len(distances) else 0
    ca = sim.two_body[closest_idx]
    fig.add_trace(
        go.Scatter3d(
            x=[ca[0]], y=[ca[1]], z=[ca[2]],
            mode="markers+text",
            text=["closest modeled point"],
            textposition="top center",
            marker={"size": 5},
            name="Modeled closest point",
        )
    )

    flyby_radius = _flyby_visual_radius_km(record, body_radius, target_scale)
    flyby_position = tuple(float(v) for v in ca)
    _add_textured_body(
        fig,
        center=flyby_position,
        radius_km=flyby_radius,
        scale=1.0,
        body_code=record.body_code if record.body_code in BODY_RADIUS_KM else central,
        texture_mode=texture_mode,
        name="Flyby object (visualized enlarged)",
        opacity=1.0,
        object_role="flyby",
        resolution=48 if texture_mode == "enhanced" else 36,
    )

    min_km = record.dist_min_au * 149_597_870.700 if record.dist_min_au is not None else None
    max_km = record.dist_max_au * 149_597_870.700 if record.dist_max_au is not None else None
    if min_km and max_km and max_km > min_km:
        fig.add_trace(
            go.Scatter3d(
                x=[0, 0], y=[min_km, max_km], z=[0, 0],
                mode="lines+markers",
                name="CAD 3-sigma miss-distance bracket",
                line={"width": 6},
            )
        )

    title = f"{record.fullname} close approach to {body_name} — {record.close_approach_date} TDB"
    texture_label = {
        "off": "flat colors",
        "simple": "simple procedural textures",
        "enhanced": "enhanced procedural textures",
    }.get(texture_mode, "flat colors")
    subtitle = (
        f"CAD nominal distance: {format_number(record.distance_ld, 3)} LD "
        f"({format_number(record.distance_km, 0)} km), v_rel {format_number(record.v_rel_kms, 2)} km/s"
        f" · visual mode: {texture_label}"
    )
    warning = "Simulation is an educational what-if from CAD summary fields, not JPL Horizons/SPICE orbit propagation."

    axis_style = {
        "backgroundcolor": palette["panel2"],
        "gridcolor": palette["grid"],
        "zerolinecolor": palette["accent"],
        "showbackground": True,
    }
    fig.update_layout(
        title={"text": f"{title}<br><sup>{subtitle}</sup>", "x": 0.02, "xanchor": "left"},
        paper_bgcolor=palette["panel"],
        plot_bgcolor=palette["panel"],
        font={"color": palette["text"], "family": "Segoe UI, Arial, sans-serif"},
        autosize=True,
        height=760,
        scene={
            "xaxis": {"title": "km, along synthetic flyby velocity", **axis_style},
            "yaxis": {"title": "km, miss-distance axis", **axis_style},
            "zaxis": {"title": "km", **axis_style},
            "aspectmode": "data",
            "bgcolor": palette["panel"],
            "camera": {"eye": {"x": 1.8, "y": 1.3, "z": 0.8}},
        },
        legend={"orientation": "h", "bgcolor": palette["panel"], "font": {"color": palette["text"]}},
        margin={"l": 0, "r": 0, "t": 90, "b": 0},
    )

    html = plot(fig, output_type="div", include_plotlyjs=True, config={"responsive": True, "displaylogo": False})
    notice_html = f"""
<details class=\"notice\"> 
<summary>Scientific note</summary>
<p><strong>Scientific limitation:</strong> {warning} The CAD API gives close-approach summary data; it does not provide the full state vector/covariance needed for reliable orbit prediction. This note can be disabled in the app options.</p>
</details>
""" if show_disclaimer else ""
    escaped_title = _html_escape(title)
    explanation = f"""
<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>{escaped_title}</title>
<style>
:root {{ color-scheme: dark; }}
html, body {{ min-height: 100%; }}
body {{ font-family: system-ui, Segoe UI, Arial, sans-serif; margin: 0; background: {palette['bg']}; color: {palette['text']}; }}
.header {{ padding: 18px 24px; background: {palette['panel']}; border-bottom: 1px solid {palette['grid']}; }}
.header h1 {{ margin: 0 0 8px 0; font-size: clamp(1.35rem, 2vw, 2.2rem); }}
.header p {{ margin: 0; color: {palette['muted']}; }}
.content {{ padding: 12px 16px 28px 16px; }}
.plot-shell {{ width: min(100%, 1500px); height: min(76vh, 860px); min-height: 560px; margin: 0 auto; background: {palette['panel']}; border: 1px solid {palette['grid']}; border-radius: 10px; overflow: hidden; box-shadow: 0 8px 18px rgba(0,0,0,0.18); }}
.plot-shell .js-plotly-plot, .plot-shell .plotly-graph-div {{ width: 100% !important; height: 100% !important; }}
.notice {{ width: min(100%, 1500px); margin: 12px auto 0 auto; padding: 10px 14px; background: {palette['notice_bg']}; border: 1px solid {palette['grid']}; border-radius: 8px; color: {palette['muted']}; }}
.notice summary {{ cursor: pointer; color: {palette['accent']}; font-weight: 700; }}
.notice p {{ margin: 8px 0 0 0; }}
code {{ color: {palette['accent']}; }}
@media (max-width: 900px) {{ .content {{ padding: 8px; }} .plot-shell {{ min-height: 460px; height: 70vh; }} }}
</style>
</head>
<body>
<div class=\"header\">
<h1>{escaped_title}</h1>
<p>{_html_escape(subtitle)}</p>
</div>
<div class=\"content\">
<div class=\"plot-shell\">
{html}
</div>
{notice_html}
</div>
</body>
</html>
"""
    html_path.write_text(explanation, encoding="utf-8")
    return html_path


def open_html(path: Path) -> None:
    webbrowser.open(path.resolve().as_uri())
