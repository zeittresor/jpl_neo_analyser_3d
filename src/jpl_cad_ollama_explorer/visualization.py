# source: https://github.com/zeittresor
from __future__ import annotations

import math
import webbrowser
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.offline import plot

from .cad_models import CadRecord, format_number
from .constants import BODY_DISPLAY, BODY_RADIUS_KM, LD_KM
from .simulator import SimulationResult


def _sphere_mesh(radius: float, scale: float = 1.0, n: int = 36) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    radius *= scale
    u = np.linspace(0, 2 * math.pi, n)
    v = np.linspace(0, math.pi, n // 2)
    x = radius * np.outer(np.cos(u), np.sin(v))
    y = radius * np.outer(np.sin(u), np.sin(v))
    z = radius * np.outer(np.ones_like(u), np.cos(v))
    return x, y, z


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


def create_visualization_html(
    record: CadRecord,
    sim: SimulationResult,
    output_dir: Path,
    target_scale: float = 20.0,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(ch if ch.isalnum() else "_" for ch in record.designation or "object")[:80]
    html_path = output_dir / f"cad_visualization_{safe_name}.html"

    central = sim.central_body
    body_name = BODY_DISPLAY.get(central, central)
    body_radius = BODY_RADIUS_KM.get(central, BODY_RADIUS_KM["Earth"])
    x, y, z = _sphere_mesh(body_radius, scale=target_scale)

    fig = go.Figure()
    fig.add_trace(
        go.Surface(
            x=x,
            y=y,
            z=z,
            opacity=0.45,
            showscale=False,
            name=f"{body_name} (scaled {target_scale:g}x)",
            hoverinfo="skip",
        )
    )

    _add_path(fig, sim.straight, "Straight-line CAD geometry", width=3, dash="dash")
    _add_path(fig, sim.two_body, f"{body_name} gravity only", width=5)
    if sim.n_body is not None:
        _add_path(fig, sim.n_body, "Approx. Sun + planet tidal perturbations", width=4)

    # Mark closest approach of the two-body path.
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

    min_km = record.dist_min_au * 149_597_870.700 if record.dist_min_au is not None else None
    max_km = record.dist_max_au * 149_597_870.700 if record.dist_max_au is not None else None
    if min_km and max_km and max_km > min_km:
        # A simple uncertainty bracket on the miss-distance axis.
        fig.add_trace(
            go.Scatter3d(
                x=[0, 0], y=[min_km, max_km], z=[0, 0],
                mode="lines+markers",
                name="CAD 3-sigma miss-distance bracket",
                line={"width": 6},
            )
        )

    title = f"{record.fullname} close approach to {body_name} — {record.close_approach_date} TDB"
    subtitle = (
        f"CAD nominal distance: {format_number(record.distance_ld, 3)} LD "
        f"({format_number(record.distance_km, 0)} km), v_rel {format_number(record.v_rel_kms, 2)} km/s"
    )
    warning = "Simulation is an educational what-if from CAD summary fields, not JPL Horizons/SPICE orbit propagation."

    fig.update_layout(
        title=f"{title}<br><sup>{subtitle}<br>{warning}</sup>",
        scene={
            "xaxis_title": "km, along synthetic flyby velocity",
            "yaxis_title": "km, miss-distance axis",
            "zaxis_title": "km",
            "aspectmode": "data",
        },
        legend={"orientation": "h"},
        margin={"l": 0, "r": 0, "t": 90, "b": 0},
    )

    html = plot(fig, output_type="div", include_plotlyjs=True)
    explanation = f"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: system-ui, Segoe UI, Arial, sans-serif; margin: 0; background: #10131a; color: #e6e6e6; }}
.header {{ padding: 18px 24px; background: #171b24; border-bottom: 1px solid #333b4c; }}
.notice {{ padding: 12px 24px; background: #332710; border-bottom: 1px solid #6c5520; }}
.content {{ padding: 0 8px 24px 8px; }}
code {{ color: #ffeeaa; }}
</style>
</head>
<body>
<div class="header">
<h1>{title}</h1>
<p>{subtitle}</p>
</div>
<div class="notice">
<strong>Scientific limitation:</strong> {warning} The CAD API gives close-approach summary data; it does not provide the full state vector/covariance needed for reliable orbit prediction. Use this view to understand scale, direction, speed and sensitivity only.
</div>
<div class="content">
{html}
</div>
</body>
</html>
"""
    html_path.write_text(explanation, encoding="utf-8")
    return html_path


def open_html(path: Path) -> None:
    webbrowser.open(path.resolve().as_uri())
