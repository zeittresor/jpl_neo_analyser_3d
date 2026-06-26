# source: https://github.com/zeittresor
from __future__ import annotations

import json
import math
import random
import sys
import traceback
import time
from pathlib import Path
from typing import Any

from .cad_models import CadRecord, format_number
from .constants import BODY_DISPLAY, BODY_RADIUS_KM
from .simulator import SimulationResult
from .surface_view import _neo_view, _sanitize_name, _select_path, _select_time_window, _surface_sky


def _sample_indices(length: int, max_points: int = 360) -> list[int]:
    if length <= 0:
        return []
    if length <= max_points:
        return list(range(length))
    step = (length - 1) / float(max_points - 1)
    out = sorted({round(i * step) for i in range(max_points)})
    if out[-1] != length - 1:
        out.append(length - 1)
    return [max(0, min(length - 1, int(i))) for i in out]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        value_f = float(value)
    except Exception:
        return default
    if not math.isfinite(value_f):
        return default
    return value_f


def _body_scene(body_code: str, viewpoint: str) -> dict[str, Any]:
    body_name = BODY_DISPLAY.get(body_code, body_code)
    key = body_code.lower()
    if viewpoint == "neo":
        return {
            "scene_name": "Flyby object surface",
            "sky_top": [2, 4, 18],
            "sky_bottom": [7, 10, 30],
            "ground": [44, 39, 38],
            "ground_far": [70, 64, 62],
            "accent": [160, 210, 255],
            "fog": [18, 18, 24],
            "terrain": "asteroid",
            "body_name": body_name,
        }
    if body_code == "Earth":
        return {
            "scene_name": "Earth stylized forest overlook",
            "sky_top": [42, 82, 132],
            "sky_bottom": [176, 215, 220],
            "ground": [35, 94, 48],
            "ground_far": [92, 145, 65],
            "accent": [105, 230, 255],
            "fog": [68, 92, 88],
            "terrain": "forest",
            "visual_style": "stylized_low_poly",
            "body_name": body_name,
        }
    if body_code == "Mars":
        return {
            "scene_name": "Mars red hillscape",
            "sky_top": [28, 11, 10],
            "sky_bottom": [82, 37, 24],
            "ground": [116, 48, 30],
            "ground_far": [170, 78, 47],
            "accent": [255, 170, 95],
            "fog": [38, 15, 12],
            "terrain": "red_hills",
            "body_name": body_name,
        }
    if body_code == "Moon":
        return {
            "scene_name": "Lunar grey plain",
            "sky_top": [0, 0, 7],
            "sky_bottom": [4, 4, 12],
            "ground": [96, 96, 96],
            "ground_far": [140, 140, 140],
            "accent": [215, 230, 255],
            "fog": [8, 8, 10],
            "terrain": "craters",
            "body_name": body_name,
        }
    if body_code == "Venus":
        return {
            "scene_name": "Venus orange haze",
            "sky_top": [60, 35, 8],
            "sky_bottom": [142, 93, 35],
            "ground": [93, 67, 38],
            "ground_far": [164, 119, 60],
            "accent": [255, 210, 110],
            "fog": [78, 44, 14],
            "terrain": "haze",
            "body_name": body_name,
        }
    if body_code == "Neptn":
        return {
            "scene_name": "Neptune icy moon overlook",
            "sky_top": [4, 8, 30],
            "sky_bottom": [16, 42, 96],
            "ground": [58, 78, 95],
            "ground_far": [104, 132, 156],
            "accent": [150, 225, 255],
            "fog": [8, 18, 32],
            "terrain": "ice_wind",
            "body_name": body_name,
        }
    if body_code in {"Juptr", "Satrn", "Urnus"}:
        return {
            "scene_name": f"{body_name} system viewpoint",
            "sky_top": [8, 12, 28],
            "sky_bottom": [24, 34, 66],
            "ground": [34, 34, 48],
            "ground_far": [76, 77, 95],
            "accent": [170, 210, 255],
            "fog": [10, 12, 20],
            "terrain": "gas_giant_moon",
            "body_name": body_name,
        }
    return {
        "scene_name": f"{body_name} rocky viewpoint",
        "sky_top": [5, 7, 18],
        "sky_bottom": [28, 28, 38],
        "ground": [84, 77, 68],
        "ground_far": [128, 118, 100],
        "accent": [220, 220, 210],
        "fog": [12, 12, 16],
        "terrain": "rocky",
        "body_name": body_name,
    }


def write_game_scenario_json(
    record: CadRecord,
    sim: SimulationResult,
    output_dir: Path,
    viewpoint: str = "surface",
    span_hours: float = 24.0,
    theme_id: str | None = "ocean",
) -> Path:
    """Write a small JSON scenario for the optional Pyglet/OpenGL education mode.

    The generated scene is intentionally qualitative. It is derived from the same CAD-based synthetic
    flyby path used by the local visualizations, and it should never be presented as an observing plan,
    true rendering, or Horizons/SPICE ephemeris result.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _sanitize_name(record.designation or record.fullname)
    scenario_path = output_dir / f"cad_play_scenario_{safe_name}_{'neo' if viewpoint == 'neo' else 'surface'}.json"

    full_path = _select_path(sim)
    times_days, path = _select_time_window(sim.times_days, full_path, span_hours)
    body_code = sim.central_body
    body_radius = BODY_RADIUS_KM.get(body_code, BODY_RADIUS_KM["Earth"])
    if viewpoint == "neo":
        sky = _neo_view(path, body_radius)
        target_label = BODY_DISPLAY.get(body_code, body_code)
        mode_label = "Flyby object viewpoint"
    else:
        sky = _surface_sky(path, body_radius)
        target_label = record.fullname or record.designation or "flyby object"
        mode_label = "Target surface viewpoint"

    low_d, nominal_d, high_d = record.estimated_diameter_range_km()
    samples = []
    for idx in _sample_indices(len(times_days)):
        sample = {
            "t_hours": _safe_float(times_days[idx] * 24.0),
            "az_deg": _safe_float(sky["az"][idx]),
            "elev_deg": _safe_float(sky["elev"][idx]),
            "distance_km": _safe_float(sky["distance"][idx]),
        }
        if viewpoint == "neo":
            sample["angular_diameter_deg"] = _safe_float(sky.get("angular_diameter", [0.0])[idx])  # type: ignore[index]
        samples.append(sample)

    payload = {
        "schema": "jpl_cad_ollama_explorer.pygame_scenario.v1",
        "visual_style": "stylized_low_poly_education_scene",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "object_name": record.fullname or record.designation or "selected object",
        "target_label": target_label,
        "mode": "neo" if viewpoint == "neo" else "surface",
        "mode_label": mode_label,
        "body_code": body_code,
        "body_name": BODY_DISPLAY.get(body_code, body_code),
        "scene": _body_scene(body_code, "neo" if viewpoint == "neo" else "surface"),
        "close_approach_date_tdb": record.close_approach_date,
        "nominal_distance_km": record.distance_km,
        "relative_speed_kms": record.v_rel_kms,
        "diameter_nominal_km": nominal_d,
        "diameter_low_km": low_d,
        "diameter_high_km": high_d,
        "span_hours": float(span_hours),
        "theme_id": theme_id or "ocean",
        "samples": samples,
        "controls": {
            "move": "WASD",
            "look": "mouse",
            "telescope": "T",
            "zoom": "mouse wheel",
            "pause": "Space",
            "time_speed": "1/2 or +/-",
            "fullscreen_toggle": "F11",
            "quit": "Esc",
        },
        "audio": {
            "ambient": "procedural",
            "footsteps": "procedural",
            "telescope_switch": "procedural",
        },
        "warning": (
            "Educational stylized game-like visualization only: synthetic CAD-derived sky direction, not a real landscape, "
            "observer ephemeris, light curve, weather, atmosphere, or visibility forecast."
        ),
    }
    scenario_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return scenario_path


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_color(a: list[int] | tuple[int, int, int], b: list[int] | tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(_lerp(float(a[i]), float(b[i]), t)))) for i in range(3))  # type: ignore[return-value]


def _angle_delta(a: float, b: float) -> float:
    return ((a - b + 180.0) % 360.0) - 180.0


def _project(az: float, elev: float, yaw: float, pitch: float, width: int, height: int, zoom: float) -> tuple[float, float, bool]:
    fov_h = max(10.0, 76.0 / max(1.0, zoom))
    fov_v = fov_h * height / max(1, width)
    dx = _angle_delta(az, yaw)
    dy = elev - pitch
    visible = abs(dx) < fov_h * 0.64 and abs(dy) < fov_v * 0.8
    x = width * 0.5 + math.tan(math.radians(dx)) / math.tan(math.radians(fov_h * 0.5)) * width * 0.5
    y = height * 0.5 - math.tan(math.radians(dy)) / math.tan(math.radians(fov_v * 0.5)) * height * 0.5
    return x, y, visible


def _interpolated_sample(samples: list[dict[str, Any]], t_hours: float) -> dict[str, float]:
    if not samples:
        return {"t_hours": 0.0, "az_deg": 0.0, "elev_deg": 30.0, "distance_km": 0.0, "angular_diameter_deg": 0.0}
    if len(samples) == 1:
        return {k: _safe_float(v) for k, v in samples[0].items()}
    if t_hours <= _safe_float(samples[0].get("t_hours")):
        return {k: _safe_float(v) for k, v in samples[0].items()}
    for left, right in zip(samples, samples[1:]):
        t0 = _safe_float(left.get("t_hours"))
        t1 = _safe_float(right.get("t_hours"))
        if t0 <= t_hours <= t1 and t1 != t0:
            f = (t_hours - t0) / (t1 - t0)
            keys = set(left) | set(right)
            return {k: _lerp(_safe_float(left.get(k)), _safe_float(right.get(k)), f) for k in keys}
    return {k: _safe_float(v) for k, v in samples[-1].items()}


def _draw_gradient(screen: Any, top: list[int], bottom: list[int]) -> None:
    import pygame

    w, h = screen.get_size()
    # Clear the whole frame before drawing the software-3D world.  Older builds only
    # repainted the upper sky area and relied on projected terrain to cover the rest
    # of the backbuffer.  When the camera looked up/down or polygons were clipped,
    # stale pixels from previous frames stayed visible as a fixed horizontal strip.
    screen.fill(tuple(bottom))
    for y in range(h):
        t = y / max(1, h - 1)
        pygame.draw.line(screen, _lerp_color(top, bottom, t), (0, y), (w, y))



def _shade(color: list[int] | tuple[int, int, int], amount: int) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c) + amount)) for c in color)  # type: ignore[return-value]


def _mul_color(color: list[int] | tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(float(c) * factor))) for c in color)  # type: ignore[return-value]


def _draw_low_poly_sky_details(screen: Any, scene: dict[str, Any], scenario: dict[str, Any], yaw: float, pitch: float, zoom: float, rng_seed: int) -> None:
    """Draw decorative, stylized sky bodies.

    This is intentionally not an astronomical renderer. It adds atmosphere to the optional game-like
    education mode while the marked target still comes from the CAD-derived synthetic sky path.
    """
    import pygame

    w, h = screen.get_size()
    terrain = str(scene.get("terrain", "rocky"))
    accent = tuple(scene.get("accent", [160, 210, 255]))
    if terrain == "forest":
        # A warm, low sun/moon disk gives the forest mode a stylized adventure-game feel.
        sx, sy, visible = _project(225.0, 28.0, yaw, pitch, w, h, max(1.0, zoom * 0.75))
        if visible:
            center = (int(sx), int(sy))
            pygame.draw.circle(screen, (255, 220, 135), center, 44)
            pygame.draw.circle(screen, (255, 245, 190), (center[0] - 10, center[1] - 9), 18)
            pygame.draw.circle(screen, (255, 220, 135), center, 48, 2)
    elif terrain in {"red_hills", "haze"}:
        sx, sy, visible = _project(250.0, 18.0, yaw, pitch, w, h, max(1.0, zoom * 0.8))
        if visible:
            pygame.draw.circle(screen, (255, 145, 80), (int(sx), int(sy)), 52)
            pygame.draw.circle(screen, (255, 205, 125), (int(sx) - 14, int(sy) - 10), 22)
    elif terrain in {"ice_wind", "gas_giant_moon"}:
        sx, sy, visible = _project(190.0, 26.0, yaw, pitch, w, h, max(1.0, zoom * 0.65))
        if visible:
            pygame.draw.circle(screen, (75, 120, 215), (int(sx), int(sy)), 74)
            pygame.draw.arc(screen, (170, 215, 255), (int(sx) - 92, int(sy) - 30, 184, 60), 0.05, 3.08, 3)
            pygame.draw.circle(screen, (150, 225, 255), (int(sx) - 20, int(sy) - 15), 20)
    else:
        sx, sy, visible = _project(215.0, 20.0, yaw, pitch, w, h, max(1.0, zoom * 0.75))
        if visible:
            pygame.draw.circle(screen, _mul_color(accent, 0.65), (int(sx), int(sy)), 38)
            pygame.draw.circle(screen, _shade(accent, 35), (int(sx) - 10, int(sy) - 7), 13)


def _draw_low_poly_tree(screen: Any, x: int, y: int, scale: float, base_color: tuple[int, int, int], trunk_color: tuple[int, int, int]) -> None:
    import pygame

    trunk_w = max(3, int(8 * scale))
    trunk_h = max(14, int(44 * scale))
    pygame.draw.polygon(
        screen,
        trunk_color,
        [(x - trunk_w, y), (x + trunk_w, y), (x + trunk_w // 2, y - trunk_h), (x - trunk_w // 2, y - trunk_h)],
    )
    # Layered triangular crowns with a darker outline and a small highlight. This gives the mode a
    # deliberately low-poly/cartoon look without shipping any copyrighted or external art assets.
    for layer in range(3):
        ly = y - trunk_h - int(layer * 22 * scale)
        half = int((34 - layer * 5) * scale)
        top = ly - int((38 - layer * 4) * scale)
        color = _shade(base_color, layer * 10)
        outline = _shade(color, -35)
        pts = [(x, top), (x - half, ly + half // 2), (x + half, ly + half // 2)]
        pygame.draw.polygon(screen, outline, [(px, py + 2) for px, py in pts])
        pygame.draw.polygon(screen, color, pts)
        pygame.draw.polygon(screen, _shade(color, 24), [(x, top + 6), (x - half // 3, ly + half // 2 - 3), (x + 3, ly + half // 2 - 2)])


def _draw_low_poly_rock(screen: Any, x: int, y: int, radius: int, color: tuple[int, int, int]) -> None:
    import pygame

    r = max(4, radius)
    pts = [(x - r * 2, y + r // 2), (x - r, y - r), (x + r // 2, y - r - 2), (x + r * 2, y), (x + r, y + r)]
    pygame.draw.polygon(screen, _shade(color, -38), [(px, py + 3) for px, py in pts])
    pygame.draw.polygon(screen, color, pts)
    pygame.draw.polygon(screen, _shade(color, 28), [pts[1], pts[2], (x, y + r // 4), (x - r, y + r // 4)])


# --- Lightweight software-3D renderer for the optional legacy Pygame fallback education mode ---
# The original game-like view is intentionally implemented without external assets or an OpenGL
# dependency.  It is not a full engine, but it renders a real X/Y/Z scene: camera position, yaw,
# pitch, perspective projection, depth sorted low-poly faces, simple terrain, rocks and tree meshes.

Vec3 = tuple[float, float, float]
Face = tuple[float, list[tuple[int, int]], tuple[int, int, int]]


def _deterministic_rng(seed: int, *coords: int) -> random.Random:
    h = seed & 0xFFFFFFFF
    for c in coords:
        h = ((h * 1664525) + (int(c) * 1013904223) + 0x9E3779B9) & 0xFFFFFFFF
    return random.Random(h)


def _terrain_height(x: float, z: float, terrain: str) -> float:
    if terrain == "forest":
        return math.sin(x * 0.013) * 0.55 + math.sin(z * 0.009) * 0.65 + math.sin((x + z) * 0.006) * 0.35
    if terrain == "red_hills":
        return math.sin(x * 0.011) * 1.0 + math.sin(z * 0.008) * 1.2 + math.sin((x - z) * 0.004) * 2.5
    if terrain == "haze":
        return math.sin(x * 0.006) * 0.8 + math.sin(z * 0.007) * 0.9
    if terrain == "ice_wind":
        return math.sin(x * 0.018) * 0.35 + math.sin(z * 0.012) * 0.55
    return math.sin(x * 0.015) * 0.45 + math.sin(z * 0.012) * 0.45


def _world_to_camera(point: Vec3, camera: Vec3, yaw: float, pitch: float) -> Vec3:
    px, py, pz = point
    cx, cy, cz = camera
    dx, dy, dz = px - cx, py - cy, pz - cz
    yaw_rad = math.radians(yaw)
    cos_y, sin_y = math.cos(yaw_rad), math.sin(yaw_rad)
    # yaw=0 looks along +Z; yaw=90 looks along +X.
    x1 = dx * cos_y - dz * sin_y
    z1 = dx * sin_y + dz * cos_y
    pitch_rad = math.radians(pitch)
    cos_p, sin_p = math.cos(pitch_rad), math.sin(pitch_rad)
    y2 = dy * cos_p - z1 * sin_p
    z2 = dy * sin_p + z1 * cos_p
    return x1, y2, z2


def _project_world_point(point: Vec3, camera: Vec3, yaw: float, pitch: float, width: int, height: int, zoom: float) -> tuple[float, float, float] | None:
    x, y, z = _world_to_camera(point, camera, yaw, pitch)
    if z <= 0.35:
        return None
    fov = max(18.0, min(92.0, 78.0 / max(1.0, zoom)))
    focal = (width * 0.5) / math.tan(math.radians(fov * 0.5))
    sx = width * 0.5 + x * focal / z
    sy = height * 0.5 - y * focal / z
    return sx, sy, z


def _append_face(
    faces: list[Face],
    vertices: list[Vec3],
    color: tuple[int, int, int],
    camera: Vec3,
    yaw: float,
    pitch: float,
    width: int,
    height: int,
    zoom: float,
    shade: int = 0,
) -> None:
    projected: list[tuple[int, int]] = []
    depths: list[float] = []
    for vertex in vertices:
        p = _project_world_point(vertex, camera, yaw, pitch, width, height, zoom)
        if p is None:
            return
        sx, sy, depth = p
        # Very loose screen cull: allow polygons partly outside the viewport.
        if sx < -width * 1.4 or sx > width * 2.4 or sy < -height * 1.5 or sy > height * 2.5:
            return
        projected.append((int(sx), int(sy)))
        depths.append(depth)
    if len(projected) >= 3:
        faces.append((sum(depths) / len(depths), projected, _shade(color, shade)))


def _path_center_x(z: float) -> float:
    return math.sin(z * 0.010) * 22.0 + math.sin(z * 0.003) * 34.0


def _ground_face_color(scene: dict[str, Any], terrain: str, x: float, z: float, distance: float) -> tuple[int, int, int]:
    ground = scene.get("ground", [60, 60, 60])
    far = scene.get("ground_far", [100, 100, 100])
    t = max(0.0, min(1.0, distance / 900.0))
    base = _lerp_color(ground, far, t)
    n = math.sin(x * 0.032 + z * 0.017) * 0.5 + math.sin(x * 0.014 - z * 0.020) * 0.5
    if terrain == "forest" and abs(x - _path_center_x(z)) < 18.0 + abs(z) * 0.002:
        return _shade((166, 134, 78), int(n * 12))
    if terrain == "red_hills":
        return _shade(base, int(18 * n + 5))
    if terrain == "ice_wind":
        return _shade(base, int(20 * n + 10))
    return _shade(base, int(14 * n))


def _add_ground_3d(
    faces: list[Face],
    screen_size: tuple[int, int],
    scene: dict[str, Any],
    camera: Vec3,
    yaw: float,
    pitch: float,
    zoom: float,
) -> None:
    width, height = screen_size
    terrain = str(scene.get("terrain", "rocky"))
    px, _py, pz = camera
    cell = 42.0 if terrain == "forest" else 55.0
    radius = 720.0
    min_x = math.floor((px - radius) / cell) * cell
    max_x = math.ceil((px + radius) / cell) * cell
    min_z = math.floor((pz - radius) / cell) * cell
    max_z = math.ceil((pz + radius) / cell) * cell
    x = min_x
    while x < max_x:
        z = min_z
        while z < max_z:
            cx, cz = x + cell * 0.5, z + cell * 0.5
            # Only draw mostly in front of the camera; the camera transform is cheap and avoids drawing a full world.
            _camx, _camy, camz = _world_to_camera((cx, 0.0, cz), camera, yaw, pitch)
            if -90.0 < camz < radius:
                y00 = _terrain_height(x, z, terrain)
                y10 = _terrain_height(x + cell, z, terrain)
                y11 = _terrain_height(x + cell, z + cell, terrain)
                y01 = _terrain_height(x, z + cell, terrain)
                color = _ground_face_color(scene, terrain, cx, cz, math.hypot(cx - px, cz - pz))
                _append_face(
                    faces,
                    [(x, y00, z), (x + cell, y10, z), (x + cell, y11, z + cell), (x, y01, z + cell)],
                    color,
                    camera,
                    yaw,
                    pitch,
                    width,
                    height,
                    zoom,
                )
            z += cell
        x += cell


def _add_cylinder_mesh(
    faces: list[Face],
    center: Vec3,
    radius: float,
    height: float,
    sides: int,
    color: tuple[int, int, int],
    camera: Vec3,
    yaw: float,
    pitch: float,
    width: int,
    height_px: int,
    zoom: float,
) -> None:
    cx, cy, cz = center
    bottom: list[Vec3] = []
    top: list[Vec3] = []
    for i in range(sides):
        a = 2.0 * math.pi * i / sides
        vx = cx + math.cos(a) * radius
        vz = cz + math.sin(a) * radius
        bottom.append((vx, cy, vz))
        top.append((vx, cy + height, vz))
    for i in range(sides):
        j = (i + 1) % sides
        shade = -30 + int(35 * (i / max(1, sides - 1)))
        _append_face(faces, [bottom[i], bottom[j], top[j], top[i]], color, camera, yaw, pitch, width, height_px, zoom, shade)


def _add_cone_mesh(
    faces: list[Face],
    center: Vec3,
    radius: float,
    height: float,
    sides: int,
    color: tuple[int, int, int],
    camera: Vec3,
    yaw: float,
    pitch: float,
    width: int,
    height_px: int,
    zoom: float,
) -> None:
    cx, cy, cz = center
    base: list[Vec3] = []
    for i in range(sides):
        a = 2.0 * math.pi * i / sides + 0.22
        base.append((cx + math.cos(a) * radius, cy, cz + math.sin(a) * radius))
    tip = (cx, cy + height, cz)
    for i in range(sides):
        j = (i + 1) % sides
        shade = -36 + int(58 * (i / max(1, sides - 1)))
        _append_face(faces, [base[i], base[j], tip], color, camera, yaw, pitch, width, height_px, zoom, shade)
    # Darker underside helps make it read as a 3D object rather than a flat triangle.
    for i in range(1, sides - 1):
        _append_face(faces, [base[0], base[i], base[i + 1]], color, camera, yaw, pitch, width, height_px, zoom, -55)


def _add_low_poly_tree_3d(
    faces: list[Face],
    x: float,
    z: float,
    scale: float,
    scene: dict[str, Any],
    camera: Vec3,
    yaw: float,
    pitch: float,
    width: int,
    height_px: int,
    zoom: float,
) -> None:
    terrain = str(scene.get("terrain", "forest"))
    ground_y = _terrain_height(x, z, terrain)
    trunk_color = (92, 57, 32)
    foliage = (34, 108, 54)
    if terrain != "forest":
        foliage = tuple(scene.get("accent", [120, 160, 180]))  # type: ignore[assignment]
    trunk_h = 14.0 * scale
    _add_cylinder_mesh(faces, (x, ground_y, z), 1.2 * scale, trunk_h, 6, trunk_color, camera, yaw, pitch, width, height_px, zoom)
    _add_cone_mesh(faces, (x, ground_y + trunk_h * 0.45, z), 7.0 * scale, 17.0 * scale, 7, _shade(foliage, -16), camera, yaw, pitch, width, height_px, zoom)
    _add_cone_mesh(faces, (x, ground_y + trunk_h * 0.95, z), 5.6 * scale, 15.0 * scale, 7, foliage, camera, yaw, pitch, width, height_px, zoom)
    _add_cone_mesh(faces, (x, ground_y + trunk_h * 1.40, z), 4.0 * scale, 12.0 * scale, 7, _shade(foliage, 18), camera, yaw, pitch, width, height_px, zoom)


def _add_rock_3d(
    faces: list[Face],
    x: float,
    z: float,
    scale: float,
    color: tuple[int, int, int],
    scene: dict[str, Any],
    camera: Vec3,
    yaw: float,
    pitch: float,
    width: int,
    height_px: int,
    zoom: float,
) -> None:
    terrain = str(scene.get("terrain", "rocky"))
    y = _terrain_height(x, z, terrain)
    # Irregular low-poly boulder: flattened octahedron-like object.
    pts = [
        (x - 3.0 * scale, y + 0.2 * scale, z - 2.0 * scale),
        (x + 2.6 * scale, y, z - 2.4 * scale),
        (x + 3.4 * scale, y + 0.2 * scale, z + 1.8 * scale),
        (x - 2.2 * scale, y, z + 2.8 * scale),
    ]
    top = (x + 0.2 * scale, y + 3.4 * scale, z + 0.1 * scale)
    for i in range(4):
        j = (i + 1) % 4
        _append_face(faces, [pts[i], pts[j], top], color, camera, yaw, pitch, width, height_px, zoom, -20 + i * 14)
    _append_face(faces, pts, _shade(color, -46), camera, yaw, pitch, width, height_px, zoom)


def _add_world_objects_3d(
    faces: list[Face],
    screen_size: tuple[int, int],
    scene: dict[str, Any],
    camera: Vec3,
    yaw: float,
    pitch: float,
    zoom: float,
    rng_seed: int,
) -> None:
    width, height = screen_size
    terrain = str(scene.get("terrain", "rocky"))
    px, _py, pz = camera
    cell = 85.0 if terrain == "forest" else 110.0
    radius = 620.0
    min_cx = math.floor((px - radius) / cell)
    max_cx = math.ceil((px + radius) / cell)
    min_cz = math.floor((pz - radius) / cell)
    max_cz = math.ceil((pz + radius) / cell)
    for ix in range(int(min_cx), int(max_cx) + 1):
        for iz in range(int(min_cz), int(max_cz) + 1):
            rnd = _deterministic_rng(rng_seed, ix, iz)
            if terrain == "forest":
                count = 2 + rnd.randint(0, 2)
                for k in range(count):
                    x = ix * cell + rnd.uniform(8.0, cell - 8.0)
                    z = iz * cell + rnd.uniform(8.0, cell - 8.0)
                    # Keep the walking path open.
                    if abs(x - _path_center_x(z)) < 24.0:
                        continue
                    if math.hypot(x - px, z - pz) < radius:
                        _add_low_poly_tree_3d(faces, x, z, rnd.uniform(0.75, 1.55), scene, camera, yaw, pitch, width, height, zoom)
            else:
                count = 1 + rnd.randint(0, 2)
                for k in range(count):
                    x = ix * cell + rnd.uniform(8.0, cell - 8.0)
                    z = iz * cell + rnd.uniform(8.0, cell - 8.0)
                    if math.hypot(x - px, z - pz) < radius:
                        base = tuple(scene.get("ground", [90, 90, 90]))
                        if terrain == "red_hills":
                            base = (138, 62, 38)
                        elif terrain == "ice_wind":
                            base = (118, 160, 185)
                        elif terrain == "haze":
                            base = (142, 93, 47)
                        _add_rock_3d(faces, x, z, rnd.uniform(1.2, 5.5), base, scene, camera, yaw, pitch, width, height, zoom)
                if terrain == "red_hills" and rnd.random() < 0.22:
                    x = ix * cell + rnd.uniform(12.0, cell - 12.0)
                    z = iz * cell + rnd.uniform(12.0, cell - 12.0)
                    _add_rock_3d(faces, x, z, rnd.uniform(8.0, 14.0), (112, 52, 35), scene, camera, yaw, pitch, width, height, zoom)


def _draw_world_3d(screen: Any, scene: dict[str, Any], yaw: float, pitch: float, player_x: float, player_z: float, zoom: float, rng_seed: int) -> None:
    """Draw a simple but real perspective scene with X/Y/Z camera movement.

    This replaces the older parallax-layer background.  It still uses Pygame's 2D drawing API, but all
    terrain and props are generated as 3D points and projected through the current camera orientation.
    This renderer is retained only as a fallback; the primary engine is the Pyglet/OpenGL renderer below.
    """
    import pygame

    width, height = screen.get_size()
    terrain = str(scene.get("terrain", "rocky"))
    camera_y = 4.8 + _terrain_height(player_x, player_z, terrain)
    camera = (player_x, camera_y, player_z)
    faces: list[Face] = []
    _add_ground_3d(faces, (width, height), scene, camera, yaw, pitch, zoom)
    _add_world_objects_3d(faces, (width, height), scene, camera, yaw, pitch, zoom, rng_seed)
    faces.sort(key=lambda item: item[0], reverse=True)
    for depth, pts, color in faces:
        if len(pts) >= 3:
            pygame.draw.polygon(screen, color, pts)
            if depth < 220:
                pygame.draw.lines(screen, _shade(color, -28), True, pts, 1)

    # Ground-level atmospheric veil. Keep this subtle and full-frame only; do not add
    # a large fixed bottom shadow because it reads as a non-perspective 2D panel and
    # makes stale-frame bugs look worse during mouse-look testing.
    fog = tuple(scene.get("fog", [12, 12, 18]))
    veil = pygame.Surface((width, height), pygame.SRCALPHA)
    if terrain == "haze":
        veil.fill((fog[0], fog[1], fog[2], 28))
    elif terrain == "ice_wind":
        veil.fill((fog[0], fog[1], fog[2], 16))
    else:
        veil.fill((fog[0], fog[1], fog[2], 8))
    screen.blit(veil, (0, 0))
    bottom_vignette_h = max(1, int(height * 0.055))
    shadow = pygame.Surface((width, bottom_vignette_h), pygame.SRCALPHA)
    shadow.fill((0, 0, 0, 18))
    screen.blit(shadow, (0, height - bottom_vignette_h))

def _draw_starfield(screen: Any, stars: list[tuple[float, float, int]], yaw: float, pitch: float, zoom: float) -> None:
    import pygame

    w, h = screen.get_size()
    for az, elev, mag in stars:
        x, y, visible = _project(az, elev, yaw, pitch, w, h, zoom)
        if visible and 0 <= x < w and 0 <= y < h * 0.62:
            c = max(120, min(255, mag))
            pygame.draw.circle(screen, (c, c, c), (int(x), int(y)), 1)


def _draw_ground(screen: Any, scene: dict[str, Any], yaw: float, player_x: float, player_z: float, rng_seed: int) -> None:
    import pygame

    w, h = screen.get_size()
    horizon = int(h * 0.60)
    ground = scene.get("ground", [45, 45, 45])
    far = scene.get("ground_far", [90, 90, 90])
    terrain = str(scene.get("terrain", "rocky"))

    # Ground gradient base.
    for y in range(horizon, h):
        t = (y - horizon) / max(1, h - horizon)
        pygame.draw.line(screen, _lerp_color(far, ground, t), (0, y), (w, y))

    # Broad low-poly terrain facets.
    phase = math.radians(yaw * 0.7) + player_x * 0.004 + player_z * 0.002
    for layer, amp, offset, mul in [(0, 28, -6, 0.72), (1, 54, 22, 0.88), (2, 82, 58, 1.02)]:
        pts: list[tuple[int, int]] = []
        step = 96 if layer == 0 else 128
        for x in range(-step, w + step + 1, step):
            n = math.sin(x * 0.009 + phase * (1.0 + layer * 0.35)) + 0.42 * math.sin(x * 0.023 + phase * 1.7)
            y = int(horizon + offset + amp * (0.45 + 0.5 * n))
            pts.append((x, y))
        pts.extend([(w + step, h), (-step, h)])
        col = _mul_color(far if layer < 2 else ground, mul)
        pygame.draw.polygon(screen, col, pts)
        # Facet highlights.
        for i in range(0, len(pts) - 3, 2):
            pygame.draw.polygon(screen, _shade(col, 10), [pts[i], pts[i + 1], (pts[i + 1][0], h), (pts[i][0], h)])

    # A stylized path/valley helps the scene read more like a small explorable world.
    if terrain == "forest":
        path_col = (170, 138, 82)
        path_shadow = (103, 89, 55)
        wiggle = math.sin(player_x * 0.01 + yaw * 0.02) * 45
        near_left = int(w * 0.23 + wiggle)
        near_right = int(w * 0.68 + wiggle)
        far_mid = int(w * 0.50 - yaw * 0.12 % 80)
        pygame.draw.polygon(screen, path_shadow, [(far_mid - 32, horizon + 28), (far_mid + 36, horizon + 30), (near_right + 24, h), (near_left - 20, h)])
        pygame.draw.polygon(screen, path_col, [(far_mid - 26, horizon + 26), (far_mid + 28, horizon + 28), (near_right, h), (near_left, h)])
        pygame.draw.polygon(screen, (205, 176, 105), [(far_mid - 16, horizon + 29), (far_mid + 8, horizon + 31), (int(w * 0.44), h), (int(w * 0.31), h)])

    rnd = random.Random(rng_seed)
    if terrain == "forest":
        # Distant bush band.
        for i in range(42):
            x = int((i * 149 - player_x * 0.38 + yaw * 2.1) % (w + 160) - 80)
            y = int(horizon + 18 + (i * 31) % max(1, int((h - horizon) * 0.26)))
            r = 10 + (i * 7) % 20
            col = (35 + (i * 3) % 24, 96 + (i * 11) % 50, 42 + (i * 5) % 24)
            pygame.draw.polygon(screen, _shade(col, -25), [(x - r, y + r // 2), (x, y - r), (x + r, y + r // 3), (x + r // 2, y + r)])
        # Stylized pine/broadleaf mix in parallax layers.
        for layer, count, parallax, y0, yspan, scale_base in [
            (0, 46, 0.45, horizon + 28, int((h - horizon) * 0.42), 0.55),
            (1, 34, 0.82, horizon + 62, int((h - horizon) * 0.62), 0.88),
            (2, 18, 1.15, horizon + 112, int((h - horizon) * 0.78), 1.25),
        ]:
            for i in range(count):
                world = i * (127 + 19 * layer)
                x = int((world - player_x * parallax + yaw * (2.8 + layer)) % (w + 220) - 110)
                y = int(y0 + (i * 71 + layer * 37) % max(1, yspan))
                scale = scale_base + (y - horizon) / max(1, h - horizon) * 0.95
                green = (23 + layer * 8, 86 + layer * 18, 45 + layer * 7)
                trunk = (88, 55, 31)
                _draw_low_poly_tree(screen, x, y, scale, green, trunk)
    elif terrain == "red_hills":
        for i in range(26):
            x = int((i * 191 - player_x * 0.42 + yaw * 1.7) % (w + 180) - 90)
            y = int(horizon + 54 + (i * 61) % max(1, h - horizon - 80))
            r = 12 + (i * 9) % 34
            _draw_low_poly_rock(screen, x, y, r, (135, 62, 38))
        # Mesa silhouettes.
        for i in range(8):
            x = int((i * 260 - player_x * 0.16 + yaw * 0.9) % (w + 280) - 140)
            y = horizon + 8 + (i * 17) % 38
            pygame.draw.polygon(screen, (93, 40, 29), [(x - 55, y + 70), (x - 42, y + 18), (x + 38, y + 18), (x + 52, y + 70)])
            pygame.draw.rect(screen, (139, 66, 42), (x - 42, y + 14, 80, 14))
    elif terrain == "haze":
        for i in range(38):
            x = int((i * 197 - player_x * 0.45 + yaw * 1.4) % (w + 120) - 60)
            y = int(horizon + 35 + (i * 43) % max(1, h - horizon - 60))
            r = 8 + (i * 11) % 36
            pygame.draw.ellipse(screen, (min(255, ground[0] + 50), min(255, ground[1] + 25), max(0, ground[2] - 8)), (x - r, y - r // 3, r * 2, r // 2), 2)
            if i % 5 == 0:
                pygame.draw.line(screen, (255, 158, 75), (x, y + 8), (x + 22, y - 16), 2)
    elif terrain == "ice_wind":
        for i in range(48):
            x = int((i * 211 - player_x * 0.6 + yaw * 2.4) % (w + 140) - 70)
            y = int(horizon + 35 + (i * 67) % max(1, h - horizon - 70))
            length = 18 + (i * 5) % 45
            pygame.draw.line(screen, (150, 195, 220), (x, y), (x + length, y - 4), 1)
            if i % 4 == 0:
                pygame.draw.polygon(screen, (104, 154, 190), [(x, y + 24), (x + 10, y - 26), (x + 24, y + 22)])
                pygame.draw.polygon(screen, (172, 225, 245), [(x + 10, y - 22), (x + 15, y + 18), (x + 23, y + 20)])
    else:
        for i in range(34):
            x = int((i * 233 - player_x * 0.55 + yaw * 2.0) % (w + 100) - 50)
            y = int(horizon + 65 + (i * 71) % max(1, h - horizon - 80))
            r = 5 + (i * 7) % 24
            _draw_low_poly_rock(screen, x, y, r, (max(40, ground[0]), max(40, ground[1]), max(40, ground[2])))
            if terrain in {"craters", "asteroid"} and i % 3 == 0:
                pygame.draw.ellipse(screen, (max(0, ground[0] - 35), max(0, ground[1] - 35), max(0, ground[2] - 35)), (x - r * 3, y - r, r * 6, r * 2), 1)

    # Foreground vignette/shadow gives depth without relying on a real 3D engine.
    shade = pygame.Surface((w, int(h * 0.22)), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 54))
    screen.blit(shade, (0, int(h * 0.78)))


def _draw_target_marker(screen: Any, sample: dict[str, float], scenario: dict[str, Any], yaw: float, pitch: float, zoom: float, telescope: bool) -> None:
    import pygame

    w, h = screen.get_size()
    az = sample.get("az_deg", 0.0)
    elev = sample.get("elev_deg", 0.0)
    x, y, visible = _project(az, elev, yaw, pitch, w, h, zoom)
    accent = tuple(scenario.get("scene", {}).get("accent", [120, 210, 255]))
    label = str(scenario.get("target_label", "target"))
    mode = str(scenario.get("mode", "surface"))
    distance = sample.get("distance_km", 0.0)

    font = pygame.font.SysFont("consolas", 18)
    small = pygame.font.SysFont("segoeui", 14)
    if visible and -80 <= x <= w + 80 and -80 <= y <= h + 80:
        if mode == "neo":
            angular = max(0.05, sample.get("angular_diameter_deg", 0.1))
            radius = max(9, min(90, int(angular * zoom * 2.5)))
            pygame.draw.circle(screen, (74, 102, 155), (int(x), int(y)), radius)
            pygame.draw.circle(screen, (160, 190, 240), (int(x - radius * 0.25), int(y - radius * 0.22)), max(1, radius // 4))
        else:
            radius = 2 + int(max(1.0, zoom) * 1.3)
            pygame.draw.circle(screen, (245, 245, 235), (int(x), int(y)), radius)
        ring = 34 if telescope else 24
        pygame.draw.circle(screen, accent, (int(x), int(y)), ring, 2)
        pygame.draw.line(screen, accent, (int(x - ring - 12), int(y)), (int(x - ring + 5), int(y)), 1)
        pygame.draw.line(screen, accent, (int(x + ring - 5), int(y)), (int(x + ring + 12), int(y)), 1)
        pygame.draw.line(screen, accent, (int(x), int(y - ring - 12)), (int(x), int(y - ring + 5)), 1)
        pygame.draw.line(screen, accent, (int(x), int(y + ring - 5)), (int(x), int(y + ring + 12)), 1)
        text = font.render(label, True, accent)
        screen.blit(text, (int(x + ring + 8), int(y - ring)))
        detail = small.render(f"az {az:.1f}°  elev {elev:.1f}°  dist {distance:,.0f} km", True, (215, 220, 225))
        screen.blit(detail, (int(x + ring + 8), int(y - ring + 24)))
    else:
        # Edge indicator when target is outside the current view.
        dx = _angle_delta(az, yaw)
        side = "left" if dx < 0 else "right"
        px = 24 if side == "left" else w - 24
        py = h // 2
        points = [(px + (10 if side == "left" else -10), py), (px - (8 if side == "left" else -8), py - 12), (px - (8 if side == "left" else -8), py + 12)]
        pygame.draw.polygon(screen, accent, points)
        txt = small.render(f"{label} {abs(dx):.0f}° {side}", True, accent)
        screen.blit(txt, (36 if side == "left" else w - txt.get_width() - 36, py - 28))


def _draw_hud(screen: Any, scenario: dict[str, Any], sample: dict[str, float], yaw: float, pitch: float, zoom: float, paused: bool, speed: float, telescope: bool) -> None:
    import pygame

    w, h = screen.get_size()
    font = pygame.font.SysFont("segoeui", 17)
    small = pygame.font.SysFont("consolas", 14)
    panel = pygame.Surface((min(w - 24, 820), 112), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 135))
    screen.blit(panel, (12, 12))
    lines = [
        f"Play this scenario — {scenario.get('object_name', 'selected object')}",
        f"{scenario.get('mode_label', '')} · {scenario.get('scene', {}).get('scene_name', '')}",
        f"t={sample.get('t_hours', 0.0):+.2f} h from modeled CA · speed {speed:g}x · {'PAUSED' if paused else 'running'} · zoom {zoom:.1f}x{' telescope' if telescope else ''}",
        "WASD move · mouse look · wheel zoom · T telescope · Space pause · 1/2 or +/- speed · F11 fullscreen · F1 help · Esc quit",
    ]
    for i, line in enumerate(lines):
        color = (225, 232, 240) if i < 2 else (185, 195, 205)
        screen.blit(font.render(line, True, color), (24, 21 + i * 24))
    warn = str(scenario.get("warning", ""))
    if warn:
        txt = small.render("Educational approximation only — not a real observing or impact/visibility forecast.", True, (255, 210, 100))
        screen.blit(txt, (12, h - 26))


def _make_sound_from_samples(pygame: Any, samples: list[int]) -> Any | None:
    try:
        import array
        buf = array.array("h", [max(-32767, min(32767, int(v))) for v in samples])
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except Exception:
        return None


def _make_tone(pygame: Any, freq: float = 880.0, duration: float = 0.16, volume: float = 0.25, rate: int = 22050) -> Any | None:
    count = max(1, int(duration * rate))
    samples = []
    for i in range(count):
        t = i / rate
        env = max(0.0, 1.0 - i / count)
        samples.append(int(math.sin(2.0 * math.pi * freq * t) * 32767 * volume * env))
    return _make_sound_from_samples(pygame, samples)


def _make_noise(pygame: Any, duration: float = 2.2, volume: float = 0.18, tone: str = "wind", rate: int = 22050) -> Any | None:
    rnd = random.Random(hash(tone) & 0xFFFF)
    count = max(1, int(duration * rate))
    samples: list[int] = []
    state = 0.0
    for i in range(count):
        white = rnd.uniform(-1.0, 1.0)
        # Low-pass filtered noise gives wind/fire/forest-like loops without extra files.
        alpha = 0.012 if tone in {"wind", "ice"} else 0.05
        state = state * (1.0 - alpha) + white * alpha
        shimmer = math.sin(i * (0.006 if tone != "fire" else 0.028)) * 0.25
        if tone == "forest":
            val = state * 0.70 + rnd.uniform(-0.2, 0.2) * 0.18
        elif tone == "fire":
            val = state * 0.55 + abs(white) * 0.22 + shimmer * 0.2
        elif tone == "ice":
            val = state * 0.85 + shimmer * 0.12
        else:
            val = state * 0.9
        samples.append(int(max(-1.0, min(1.0, val)) * 32767 * volume))
    return _make_sound_from_samples(pygame, samples)


def _create_soundscape(pygame: Any, scene: dict[str, Any]) -> dict[str, Any | None]:
    sounds: dict[str, Any | None] = {"ambient": None, "step": None, "telescope": None}
    try:
        if not pygame.mixer.get_init():
            return sounds
        terrain = str(scene.get("terrain", "rocky"))
        body_name = str(scene.get("body_name", ""))
        if terrain == "forest":
            ambient = _make_noise(pygame, tone="forest", volume=0.16)
        elif terrain == "haze" or body_name == "Venus":
            ambient = _make_noise(pygame, tone="fire", volume=0.18)
        elif terrain == "ice_wind" or body_name == "Neptune":
            ambient = _make_noise(pygame, tone="ice", volume=0.17)
        else:
            ambient = _make_noise(pygame, tone="wind", volume=0.12)
        step = _make_noise(pygame, duration=0.12, volume=0.22, tone="step")
        telescope = _make_tone(pygame, freq=740.0, duration=0.08, volume=0.18)
        sounds.update({"ambient": ambient, "step": step, "telescope": telescope})
        if ambient is not None:
            ambient.play(loops=-1, fade_ms=500)
    except Exception:
        pass
    return sounds



def run_pygame_scenario(scenario_path: Path) -> int:
    try:
        import pygame
    except Exception as exc:  # pragma: no cover - exercised on machines without pygame
        print("Pygame is not installed. Install optional dependency with: .venv\\Scripts\\python.exe -m pip install pygame")
        print(f"Import error: {exc}")
        return 3

    scenario = json.loads(Path(scenario_path).read_text(encoding="utf-8"))
    samples = scenario.get("samples") or []
    if not samples:
        print("Scenario contains no samples.")
        return 2

    try:
        pygame.mixer.pre_init(22050, -16, 1, 512)
    except Exception:
        pass
    pygame.init()
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(22050, -16, 1, 512)
    except Exception:
        pass
    pygame.display.set_caption(f"JPL CAD Play Scenario - {scenario.get('object_name', '')}")
    fullscreen = True
    try:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    except Exception:
        fullscreen = False
        screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)

    scene = scenario.get("scene", {})
    sounds = _create_soundscape(pygame, scene)
    last_step_sound_at = 0.0
    seed = abs(hash(str(scenario.get("object_name", "scenario")))) % 2_000_000
    random.seed(seed)
    stars = [(random.random() * 360.0, random.uniform(-10.0, 88.0), random.randint(150, 255)) for _ in range(520)]
    yaw = 0.0
    pitch = 8.0
    zoom = 1.0
    telescope = False
    paused = False
    speed = 1.0
    t_min = _safe_float(samples[0].get("t_hours"))
    t_max = _safe_float(samples[-1].get("t_hours"), 1.0)
    t_current = t_min
    player_x = 0.0
    player_z = 0.0
    show_help = False

    # Start roughly facing the first above-horizon point if possible.
    for s in samples:
        if _safe_float(s.get("elev_deg")) >= 0:
            yaw = _safe_float(s.get("az_deg"))
            pitch = max(-20.0, min(45.0, _safe_float(s.get("elev_deg")) * 0.6))
            break

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_t:
                    telescope = not telescope
                    zoom = 4.0 if telescope and zoom < 2.5 else (1.0 if not telescope and zoom > 3.0 else zoom)
                    snd = sounds.get("telescope")
                    if snd is not None:
                        try:
                            snd.play()
                        except Exception:
                            pass
                elif event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    try:
                        if fullscreen:
                            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        else:
                            screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
                    except Exception:
                        fullscreen = False
                        screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
                elif event.key == pygame.K_F1:
                    show_help = not show_help
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_2):
                    speed = min(128.0, speed * 2.0)
                elif event.key in (pygame.K_MINUS, pygame.K_1):
                    speed = max(0.125, speed / 2.0)
            elif event.type == pygame.MOUSEMOTION:
                mx, my = event.rel
                sensitivity = 0.09 / max(1.0, math.sqrt(zoom))
                yaw = (yaw + mx * sensitivity) % 360.0
                pitch = max(-82.0, min(88.0, pitch - my * sensitivity))
            elif event.type == pygame.MOUSEWHEEL:
                zoom = max(1.0, min(16.0, zoom * (1.15 ** event.y)))
                telescope = zoom >= 3.0

        keys = pygame.key.get_pressed()
        move_speed = 90.0 * dt
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            move_speed *= 2.5
        yaw_rad = math.radians(yaw)
        forward_x = math.sin(yaw_rad)
        forward_z = math.cos(yaw_rad)
        right_x = math.cos(yaw_rad)
        right_z = -math.sin(yaw_rad)
        if keys[pygame.K_w]:
            player_x += forward_x * move_speed
            player_z += forward_z * move_speed
        if keys[pygame.K_s]:
            player_x -= forward_x * move_speed
            player_z -= forward_z * move_speed
        if keys[pygame.K_d]:
            player_x += right_x * move_speed
            player_z += right_z * move_speed
        if keys[pygame.K_a]:
            player_x -= right_x * move_speed
            player_z -= right_z * move_speed

        moving = bool(keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d])
        if moving and time.monotonic() - last_step_sound_at > (0.42 if move_speed < 0.3 else 0.24):
            snd = sounds.get("step")
            if snd is not None:
                try:
                    snd.play()
                except Exception:
                    pass
            last_step_sound_at = time.monotonic()

        if not paused:
            t_current += dt * speed
            if t_current > t_max:
                t_current = t_min
        sample = _interpolated_sample(samples, t_current)

        _draw_gradient(screen, scene.get("sky_top", [5, 8, 18]), scene.get("sky_bottom", [24, 34, 58]))
        _draw_starfield(screen, stars, yaw, pitch, zoom)
        _draw_low_poly_sky_details(screen, scene, scenario, yaw, pitch, zoom, seed)
        _draw_world_3d(screen, scene, yaw, pitch, player_x, player_z, zoom, seed)
        _draw_target_marker(screen, sample, scenario, yaw, pitch, zoom, telescope)
        _draw_hud(screen, scenario, sample, yaw, pitch, zoom, paused, speed, telescope)

        if show_help:
            help_font = pygame.font.SysFont("segoeui", 18)
            box = pygame.Surface((640, 230), pygame.SRCALPHA)
            box.fill((0, 0, 0, 190))
            screen.blit(box, (screen.get_width() // 2 - 320, screen.get_height() // 2 - 115))
            help_lines = [
                "This is a playful educational view, not a real ephemeris renderer.",
                "The marker follows the synthetic CAD-derived sky direction.",
                "Use it to build intuition: where would the object appear, roughly?",
                "For real observation planning use JPL Horizons/SPICE, lighting and local geography.",
                "F1 closes this help overlay.",
            ]
            for i, line in enumerate(help_lines):
                screen.blit(help_font.render(line, True, (230, 235, 240)), (screen.get_width() // 2 - 292, screen.get_height() // 2 - 82 + i * 34))

        pygame.display.flip()

    try:
        pygame.mixer.fadeout(250)
    except Exception:
        pass
    pygame.event.set_grab(False)
    pygame.mouse.set_visible(True)
    pygame.quit()
    return 0



# --- Pyglet/OpenGL first-person 3D renderer for the optional education/game mode ---
# This is the primary interactive scenario engine as of v0.1.40.  It uses pyglet to create
# a real OpenGL scene with a first-person camera, procedural terrain textures and simple
# generated low-poly meshes.  The older Pygame software renderer is kept below as a fallback
# for systems where pyglet/OpenGL cannot initialize.


def _scene_color_tuple(scene: dict[str, Any], key: str, default: tuple[int, int, int]) -> tuple[int, int, int]:
    value = scene.get(key, default)
    try:
        return (int(value[0]), int(value[1]), int(value[2]))
    except Exception:
        return default


def _normalize(v: Vec3) -> Vec3:
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length <= 1e-9:
        return (0.0, 0.0, 1.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _surface_normal(x: float, z: float, terrain: str) -> Vec3:
    eps = 2.0
    h_l = _terrain_height(x - eps, z, terrain)
    h_r = _terrain_height(x + eps, z, terrain)
    h_d = _terrain_height(x, z - eps, terrain)
    h_u = _terrain_height(x, z + eps, terrain)
    return _normalize((h_l - h_r, eps * 2.0, h_d - h_u))


def _make_procedural_texture_bytes(scene: dict[str, Any], kind: str = "ground", size: int = 64) -> bytes:
    terrain = str(scene.get("terrain", "rocky"))
    ground = _scene_color_tuple(scene, "ground", (75, 75, 75))
    far = _scene_color_tuple(scene, "ground_far", (115, 115, 115))
    data = bytearray()
    rng = random.Random(f"{terrain}:{kind}:jpl-cad")
    for y in range(size):
        for x in range(size):
            nx = x / max(1, size - 1)
            ny = y / max(1, size - 1)
            noise = (math.sin(x * 0.41 + y * 0.19) + math.sin(x * 0.13 - y * 0.31) + rng.uniform(-0.35, 0.35)) / 2.8
            if terrain == "forest":
                base = ground if kind == "ground" else (38, 114, 52)
                path = abs((nx - 0.5) + math.sin(ny * 7.0) * 0.08)
                if kind == "ground" and path < 0.11:
                    base = (164, 130, 75)
                r, g, b = _shade(base, int(noise * 34))
                if kind == "ground" and rng.random() < 0.07:
                    g = min(255, g + 26)
            elif terrain == "red_hills":
                base = (146, 61, 34) if kind == "ground" else (118, 55, 38)
                stripe = math.sin((nx + ny) * 24.0) * 0.5
                r, g, b = _shade(base, int((noise + stripe) * 30))
            elif terrain == "haze":
                base = (130, 86, 45)
                sulfur = math.sin(nx * 18.0) * math.sin(ny * 11.0)
                r, g, b = _shade(base, int((noise + sulfur * 0.4) * 28))
            elif terrain == "ice_wind":
                base = (88, 130, 160)
                ice = max(0.0, math.sin((nx - ny) * 31.0))
                r, g, b = _shade(base, int(noise * 22 + ice * 38))
            else:
                base = ground
                r, g, b = _shade(base, int(noise * 32))
            # Slight distance/facet color hint.
            if kind == "far":
                r, g, b = _lerp_color([r, g, b], far, 0.35)
            data.extend([max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))])
    return bytes(data)


def _az_el_to_vec(az_deg: float, elev_deg: float) -> Vec3:
    az = math.radians(az_deg)
    el = math.radians(elev_deg)
    ce = math.cos(el)
    return (math.sin(az) * ce, math.sin(el), math.cos(az) * ce)


def _run_pyglet_scenario_impl(scenario_path: Path) -> int:
    try:
        import pyglet
        from pyglet.window import key, mouse
        from pyglet import gl
    except Exception as exc:  # pragma: no cover - exercised on machines without pyglet
        print("pyglet is not installed. Install it with: .venv\\Scripts\\python.exe -m pip install pyglet")
        print(f"Import error: {exc}")
        return 3

    scenario = json.loads(Path(scenario_path).read_text(encoding="utf-8"))
    samples = scenario.get("samples") or []
    if not samples:
        print("Scenario contains no samples.")
        return 2

    scene = scenario.get("scene", {}) if isinstance(scenario.get("scene"), dict) else {}
    terrain = str(scene.get("terrain", "rocky"))
    sky_top = _scene_color_tuple(scene, "sky_top", (8, 12, 28))
    sky_bottom = _scene_color_tuple(scene, "sky_bottom", (32, 44, 70))
    ground_color = _scene_color_tuple(scene, "ground", (80, 80, 80))
    far_color = _scene_color_tuple(scene, "ground_far", (120, 120, 120))
    accent_color = _scene_color_tuple(scene, "accent", (180, 220, 255))
    seed = abs(hash(str(scenario.get("object_name", "scenario")))) % 2_000_000
    rng = random.Random(seed)

    try:
        config = gl.Config(double_buffer=True, depth_size=24, sample_buffers=1, samples=2)
        window = pyglet.window.Window(fullscreen=True, caption=f"JPL CAD Play Scenario - {scenario.get('object_name', '')}", config=config, vsync=True)
    except Exception:
        try:
            config = gl.Config(double_buffer=True, depth_size=24)
            window = pyglet.window.Window(1280, 720, resizable=True, caption=f"JPL CAD Play Scenario - {scenario.get('object_name', '')}", config=config, vsync=True)
        except Exception as exc:
            print(f"Could not create pyglet/OpenGL window: {exc}")
            return 4

    try:
        window.set_exclusive_mouse(True)
    except Exception:
        pass

    keys = key.KeyStateHandler()
    window.push_handlers(keys)

    state: dict[str, Any] = {
        "x": 0.0,
        "z": -18.0,
        "yaw": 0.0,
        "pitch": 8.0,
        "zoom": 1.0,
        "telescope": False,
        "paused": False,
        "speed": 1.0,
        "t_current": _safe_float(samples[0].get("t_hours")),
        "show_help": False,
        "exclusive_mouse": True,
        "last_step": 0.0,
        "walking_phase": 0.0,
    }
    t_min = _safe_float(samples[0].get("t_hours"))
    t_max = _safe_float(samples[-1].get("t_hours"), t_min + 1.0)

    for s in samples:
        if _safe_float(s.get("elev_deg")) >= 0:
            state["yaw"] = _safe_float(s.get("az_deg"))
            state["pitch"] = max(-25.0, min(55.0, _safe_float(s.get("elev_deg")) * 0.55))
            break

    try:
        raw_ground = _make_procedural_texture_bytes(scene, "ground", 64)
        ground_image = pyglet.image.ImageData(64, 64, "RGB", raw_ground, pitch=64 * 3)
        ground_texture = ground_image.get_texture()
        gl.glBindTexture(ground_texture.target, ground_texture.id)
        gl.glTexParameteri(ground_texture.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(ground_texture.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(ground_texture.target, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
        gl.glTexParameteri(ground_texture.target, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
    except Exception:
        ground_texture = None

    # Deterministic object placement.  Forest keeps a rough walking lane near the origin.
    props: list[dict[str, Any]] = []
    for iz in range(-10, 18):
        for ix in range(-10, 11):
            cell = 34.0 if terrain == "forest" else 46.0
            rnd = _deterministic_rng(seed, ix, iz)
            x = ix * cell + rnd.uniform(-cell * 0.35, cell * 0.35)
            z = iz * cell + rnd.uniform(-cell * 0.35, cell * 0.35)
            lane = abs(x - _path_center_x(z))
            if terrain == "forest":
                if lane < 15.0 or rnd.random() < 0.25:
                    continue
                props.append({"kind": "tree", "x": x, "z": z, "scale": rnd.uniform(0.75, 1.55)})
                if rnd.random() < 0.18:
                    props.append({"kind": "rock", "x": x + rnd.uniform(-8, 8), "z": z + rnd.uniform(-8, 8), "scale": rnd.uniform(0.7, 1.8)})
            else:
                if rnd.random() < 0.72:
                    props.append({"kind": "rock", "x": x, "z": z, "scale": rnd.uniform(0.9, 4.5)})
                if terrain in {"red_hills", "gas_giant_moon"} and rnd.random() < 0.10:
                    props.append({"kind": "mesa", "x": x, "z": z, "scale": rnd.uniform(2.4, 5.2)})

    stars = [(rng.random() * 360.0, rng.uniform(2.0, 88.0), rng.uniform(0.8, 1.8)) for _ in range(720)]

    fps_label = pyglet.text.Label("", x=14, y=14, anchor_x="left", anchor_y="bottom", color=(225, 235, 245, 230), font_size=10)
    help_label = pyglet.text.Label("", x=18, y=window.height - 18, anchor_x="left", anchor_y="top", width=780, multiline=True, color=(238, 240, 245, 245), font_size=12)

    def set_projection_3d() -> None:
        width = max(1, window.width)
        height = max(1, window.height)
        aspect = width / float(height)
        fov = max(18.0, min(86.0, 74.0 / max(1.0, state["zoom"])))
        near = 0.12
        far = 1800.0
        top = math.tan(math.radians(fov * 0.5)) * near
        right = top * aspect
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glFrustum(-right, right, -top, top, near, far)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

    def set_projection_2d() -> None:
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, window.width, 0, window.height, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

    def gl_color(color: tuple[int, int, int] | list[int], alpha: int = 255, shade: int = 0) -> None:
        c = _shade((int(color[0]), int(color[1]), int(color[2])), shade)
        gl.glColor4f(c[0] / 255.0, c[1] / 255.0, c[2] / 255.0, alpha / 255.0)

    def _gl_disable(name: str) -> None:
        value = getattr(gl, name, None)
        if value is None:
            return
        try:
            gl.glDisable(value)
        except Exception:
            pass

    def _gl_enable(name: str) -> None:
        value = getattr(gl, name, None)
        if value is None:
            return
        try:
            gl.glEnable(value)
        except Exception:
            pass

    def reset_scene_gl_state(*, for_2d: bool = False) -> None:
        # Pyglet text rendering and some drivers can leave texture/blend state enabled.
        # Resetting the fixed-function state at frame boundaries prevents sky/terrain
        # textures from bleeding into the background on the next mouse movement.
        _gl_disable("GL_TEXTURE_2D")
        _gl_disable("GL_LIGHTING")
        _gl_disable("GL_COLOR_MATERIAL")
        _gl_disable("GL_FOG")
        _gl_disable("GL_CULL_FACE")
        if for_2d:
            _gl_disable("GL_DEPTH_TEST")
            try:
                gl.glDepthMask(gl.GL_FALSE)
            except Exception:
                pass
        else:
            _gl_enable("GL_DEPTH_TEST")
            _gl_disable("GL_BLEND")
            try:
                gl.glDepthMask(gl.GL_TRUE)
            except Exception:
                pass
        try:
            gl.glColor4f(1.0, 1.0, 1.0, 1.0)
        except Exception:
            pass

    def dot(a: Vec3, b: Vec3) -> float:
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    def load_look_matrix(eye: Vec3, yaw_deg: float, pitch_deg: float) -> None:
        # Keep the world convention used by movement and target placement:
        # yaw 0 looks toward +Z, yaw 90 toward +X, positive pitch looks upward.
        yaw_rad = math.radians(yaw_deg)
        pitch_rad = math.radians(pitch_deg)
        cp = math.cos(pitch_rad)
        forward = _normalize((math.sin(yaw_rad) * cp, math.sin(pitch_rad), math.cos(yaw_rad) * cp))
        up_ref = (0.0, 1.0, 0.0)
        side = _normalize(_cross(forward, up_ref))
        if abs(side[0]) + abs(side[1]) + abs(side[2]) <= 1e-6:
            side = (1.0, 0.0, 0.0)
        up = _cross(side, forward)
        # OpenGL expects column-major matrices.  This is equivalent to gluLookAt
        # but avoids a GLU dependency, which is not consistently available on pyglet setups.
        matrix = (gl.GLfloat * 16)(
            side[0], up[0], -forward[0], 0.0,
            side[1], up[1], -forward[1], 0.0,
            side[2], up[2], -forward[2], 0.0,
            -dot(side, eye), -dot(up, eye), dot(forward, eye), 1.0,
        )
        gl.glMultMatrixf(matrix)

    def vertex(v: Vec3) -> None:
        gl.glVertex3f(float(v[0]), float(v[1]), float(v[2]))

    def draw_box(cx: float, cy: float, cz: float, sx: float, sy: float, sz: float, color: tuple[int, int, int]) -> None:
        x0, x1 = cx - sx * 0.5, cx + sx * 0.5
        y0, y1 = cy, cy + sy
        z0, z1 = cz - sz * 0.5, cz + sz * 0.5
        faces = [
            ([(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)], 18),
            ([(x1,y0,z0),(x0,y0,z0),(x0,y1,z0),(x1,y1,z0)], -22),
            ([(x0,y0,z0),(x0,y0,z1),(x0,y1,z1),(x0,y1,z0)], -10),
            ([(x1,y0,z1),(x1,y0,z0),(x1,y1,z0),(x1,y1,z1)], 4),
            ([(x0,y1,z1),(x1,y1,z1),(x1,y1,z0),(x0,y1,z0)], 28),
        ]
        for verts, shade in faces:
            gl_color(color, shade=shade)
            gl.glBegin(gl.GL_QUADS)
            for v in verts:
                vertex(v)  # type: ignore[arg-type]
            gl.glEnd()

    def draw_cone(cx: float, cy: float, cz: float, radius: float, height: float, sides: int, color: tuple[int, int, int]) -> None:
        gl.glBegin(gl.GL_TRIANGLES)
        for i in range(sides):
            a0 = 2.0 * math.pi * i / sides
            a1 = 2.0 * math.pi * (i + 1) / sides
            shade = -34 + int(56 * i / max(1, sides - 1))
            gl_color(color, shade=shade)
            gl.glVertex3f(cx + math.cos(a0) * radius, cy, cz + math.sin(a0) * radius)
            gl.glVertex3f(cx + math.cos(a1) * radius, cy, cz + math.sin(a1) * radius)
            gl.glVertex3f(cx, cy + height, cz)
        gl.glEnd()

    def draw_cylinder(cx: float, cy: float, cz: float, radius: float, height: float, sides: int, color: tuple[int, int, int]) -> None:
        gl.glBegin(gl.GL_QUADS)
        for i in range(sides):
            a0 = 2.0 * math.pi * i / sides
            a1 = 2.0 * math.pi * (i + 1) / sides
            shade = -28 + int(42 * i / max(1, sides - 1))
            gl_color(color, shade=shade)
            gl.glVertex3f(cx + math.cos(a0) * radius, cy, cz + math.sin(a0) * radius)
            gl.glVertex3f(cx + math.cos(a1) * radius, cy, cz + math.sin(a1) * radius)
            gl.glVertex3f(cx + math.cos(a1) * radius, cy + height, cz + math.sin(a1) * radius)
            gl.glVertex3f(cx + math.cos(a0) * radius, cy + height, cz + math.sin(a0) * radius)
        gl.glEnd()

    def draw_low_poly_tree(x: float, z: float, scale: float) -> None:
        y = _terrain_height(x, z, terrain)
        draw_cylinder(x, y, z, 0.8 * scale, 7.5 * scale, 6, (92, 57, 32))
        foliage = (35, 120, 55)
        draw_cone(x, y + 4.0 * scale, z, 5.2 * scale, 9.5 * scale, 7, _shade(foliage, -16))
        draw_cone(x, y + 8.7 * scale, z, 4.0 * scale, 8.4 * scale, 7, foliage)
        draw_cone(x, y + 12.5 * scale, z, 2.9 * scale, 6.8 * scale, 7, _shade(foliage, 18))

    def draw_rock(x: float, z: float, scale: float, color: tuple[int, int, int]) -> None:
        y = _terrain_height(x, z, terrain)
        r = max(1.0, 2.2 * scale)
        pts = [(x-r*1.3,y,z-r), (x+r,y,z-r*1.1), (x+r*1.2,y,z+r*0.9), (x-r,y,z+r*1.3)]
        top = (x + 0.15 * r, y + r * 1.4, z + 0.05 * r)
        gl.glBegin(gl.GL_TRIANGLES)
        for i in range(4):
            j = (i + 1) % 4
            gl_color(color, shade=-20 + i * 12)
            vertex(pts[i])
            vertex(pts[j])
            vertex(top)
        gl.glEnd()
        gl_color(color, shade=-48)
        gl.glBegin(gl.GL_QUADS)
        for p in pts:
            vertex(p)
        gl.glEnd()

    def draw_mesa(x: float, z: float, scale: float) -> None:
        y = _terrain_height(x, z, terrain)
        color = (126, 58, 38) if terrain == "red_hills" else _shade(ground_color, 8)
        draw_box(x, y, z, 8.0 * scale, 6.0 * scale, 7.0 * scale, color)
        draw_box(x, y + 5.8 * scale, z, 10.5 * scale, 1.8 * scale, 8.5 * scale, _shade(color, 32))

    def draw_sky_dome() -> None:
        reset_scene_gl_state(for_2d=True)
        set_projection_2d()
        h = max(1.0, float(window.height))
        w = max(1.0, float(window.width))
        fov = max(18.0, min(86.0, 74.0 / max(1.0, float(state["zoom"]))))
        # Move the visual horizon with the camera pitch so the background no longer
        # feels like a fixed 2D wallpaper when looking up or down.
        horizon_y = h * 0.50 - (float(state["pitch"]) / max(1.0, fov)) * h * 0.92
        bands = 28
        gl.glBegin(gl.GL_QUADS)
        for i in range(bands):
            y0 = h * i / bands
            y1 = h * (i + 1) / bands
            y_mid = (y0 + y1) * 0.5
            t = max(0.0, min(1.0, 0.50 + (y_mid - horizon_y) / max(1.0, h * 0.95)))
            color = _lerp_color(sky_bottom, sky_top, t)
            gl_color(color)
            gl.glVertex2f(0, y0)
            gl.glVertex2f(w, y0)
            gl.glVertex2f(w, y1)
            gl.glVertex2f(0, y1)
        gl.glEnd()
        # Subtle horizon haze that follows the view pitch instead of remaining fixed.
        haze = _scene_color_tuple(scene, "fog", (20, 20, 28))
        band = h * 0.115
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glBegin(gl.GL_QUADS)
        gl_color(haze, alpha=0)
        gl.glVertex2f(0, horizon_y + band)
        gl.glVertex2f(w, horizon_y + band)
        gl_color(haze, alpha=64)
        gl.glVertex2f(w, horizon_y)
        gl.glVertex2f(0, horizon_y)
        gl_color(haze, alpha=64)
        gl.glVertex2f(0, horizon_y)
        gl.glVertex2f(w, horizon_y)
        gl_color(haze, alpha=0)
        gl.glVertex2f(w, horizon_y - band)
        gl.glVertex2f(0, horizon_y - band)
        gl.glEnd()
        gl.glDisable(gl.GL_BLEND)
        try:
            gl.glDepthMask(gl.GL_TRUE)
        except Exception:
            pass

    def apply_camera() -> tuple[float, float, float]:
        x = float(state["x"])
        z = float(state["z"])
        eye_y = _terrain_height(x, z, terrain) + 2.4
        bob = math.sin(float(state["walking_phase"])) * 0.07
        eye = (x, eye_y + bob, z)
        load_look_matrix(eye, float(state["yaw"]), float(state["pitch"]))
        return eye

    def draw_stars(camera: Vec3) -> None:
        # Place a distant star shell in world coordinates around the camera.
        gl.glPointSize(1.4)
        gl.glBegin(gl.GL_POINTS)
        for az, elev, mag in stars:
            if elev < -2.0:
                continue
            d = _az_el_to_vec(az, elev)
            alpha_col = int(150 + min(1.0, mag / 2.0) * 92)
            gl_color((alpha_col, alpha_col, alpha_col))
            gl.glVertex3f(camera[0] + d[0] * 950.0, camera[1] + d[1] * 950.0, camera[2] + d[2] * 950.0)
        gl.glEnd()

    def draw_ground() -> None:
        cam_x = float(state["x"])
        cam_z = float(state["z"])
        cell = 18.0 if terrain == "forest" else 24.0
        radius = 620.0
        min_x = math.floor((cam_x - radius) / cell) * cell
        max_x = math.ceil((cam_x + radius) / cell) * cell
        min_z = math.floor((cam_z - radius) / cell) * cell
        max_z = math.ceil((cam_z + radius) / cell) * cell
        reset_scene_gl_state(for_2d=False)
        # Only the top side of the terrain should render.  This prevents the player
        # from seeing the underside of far terrain patches when looking steeply up/down.
        _gl_enable("GL_CULL_FACE")
        try:
            gl.glCullFace(gl.GL_BACK)
            gl.glFrontFace(gl.GL_CCW)
        except Exception:
            pass
        if ground_texture is not None:
            gl.glEnable(ground_texture.target)
            gl.glBindTexture(ground_texture.target, ground_texture.id)
        gl.glBegin(gl.GL_QUADS)
        x = min_x
        while x < max_x:
            z = min_z
            while z < max_z:
                cx = x + cell * 0.5
                cz = z + cell * 0.5
                dist = math.hypot(cx - cam_x, cz - cam_z)
                if dist <= radius:
                    y00 = _terrain_height(x, z, terrain)
                    y10 = _terrain_height(x + cell, z, terrain)
                    y11 = _terrain_height(x + cell, z + cell, terrain)
                    y01 = _terrain_height(x, z + cell, terrain)
                    normal = _surface_normal(cx, cz, terrain)
                    light = max(0.35, min(1.15, normal[1] * 0.75 + normal[0] * 0.16 + 0.30))
                    color = _ground_face_color(scene, terrain, cx, cz, dist)
                    gl_color(_mul_color(color, light))
                    tex_scale = 0.035 if terrain == "forest" else 0.026
                    # Counter-clockwise winding as seen from above (+Y normal).
                    if ground_texture is not None: gl.glTexCoord2f(x * tex_scale, z * tex_scale)
                    gl.glVertex3f(x, y00, z)
                    if ground_texture is not None: gl.glTexCoord2f(x * tex_scale, (z + cell) * tex_scale)
                    gl.glVertex3f(x, y01, z + cell)
                    if ground_texture is not None: gl.glTexCoord2f((x + cell) * tex_scale, (z + cell) * tex_scale)
                    gl.glVertex3f(x + cell, y11, z + cell)
                    if ground_texture is not None: gl.glTexCoord2f((x + cell) * tex_scale, z * tex_scale)
                    gl.glVertex3f(x + cell, y10, z)
                z += cell
            x += cell
        gl.glEnd()
        if ground_texture is not None:
            gl.glDisable(ground_texture.target)
        _gl_disable("GL_CULL_FACE")
        _gl_disable("GL_TEXTURE_2D")

    def draw_props() -> None:
        reset_scene_gl_state(for_2d=False)
        cam_x = float(state["x"])
        cam_z = float(state["z"])
        visible = [p for p in props if math.hypot(float(p["x"]) - cam_x, float(p["z"]) - cam_z) < 520.0]
        visible.sort(key=lambda p: math.hypot(float(p["x"]) - cam_x, float(p["z"]) - cam_z), reverse=True)
        for p in visible:
            x = float(p["x"])
            z = float(p["z"])
            scale = float(p.get("scale", 1.0))
            kind = str(p.get("kind", "rock"))
            if kind == "tree":
                draw_low_poly_tree(x, z, scale)
            elif kind == "mesa":
                draw_mesa(x, z, scale)
            else:
                color = ground_color
                if terrain == "red_hills": color = (138, 62, 38)
                elif terrain == "ice_wind": color = (118, 160, 185)
                elif terrain == "haze": color = (142, 93, 47)
                draw_rock(x, z, scale, color)

    def draw_target(camera: Vec3) -> None:
        reset_scene_gl_state(for_2d=False)
        sample = _interpolated_sample(samples, float(state["t_current"]))
        direction = _az_el_to_vec(float(sample.get("az_deg", 0.0)), float(sample.get("elev_deg", 22.0)))
        d = 360.0
        x = camera[0] + direction[0] * d
        y = camera[1] + direction[1] * d
        z = camera[2] + direction[2] * d
        angular = float(sample.get("angular_diameter_deg", 0.0) or 0.0)
        base_radius = 2.5 + min(18.0, max(0.0, angular) * 8.0)
        if bool(state["telescope"]):
            base_radius *= 2.4
        gl.glDisable(gl.GL_LIGHTING)
        gl.glColor3f(accent_color[0] / 255.0, accent_color[1] / 255.0, accent_color[2] / 255.0)
        draw_cylinder(x, y - base_radius * 0.5, z, base_radius * 0.05, base_radius, 8, accent_color)
        # Crosshair as 3D line segments around the target.
        gl.glLineWidth(2.0)
        gl.glBegin(gl.GL_LINES)
        gl_color(accent_color)
        right = _normalize(_cross((0.0, 1.0, 0.0), direction))
        up = _normalize(_cross(direction, right))
        for axis in (right, up):
            gl.glVertex3f(x - axis[0] * base_radius * 3.0, y - axis[1] * base_radius * 3.0, z - axis[2] * base_radius * 3.0)
            gl.glVertex3f(x - axis[0] * base_radius * 1.15, y - axis[1] * base_radius * 1.15, z - axis[2] * base_radius * 1.15)
            gl.glVertex3f(x + axis[0] * base_radius * 1.15, y + axis[1] * base_radius * 1.15, z + axis[2] * base_radius * 1.15)
            gl.glVertex3f(x + axis[0] * base_radius * 3.0, y + axis[1] * base_radius * 3.0, z + axis[2] * base_radius * 3.0)
        gl.glEnd()
        gl.glLineWidth(1.0)

    def draw_environment_effects(camera: Vec3) -> None:
        reset_scene_gl_state(for_2d=False)
        if terrain == "ice_wind":
            gl.glBegin(gl.GL_LINES)
            for i in range(70):
                rnd = _deterministic_rng(seed, i, int(float(state["t_current"]) * 10))
                x = camera[0] + rnd.uniform(-160, 160)
                y = camera[1] + rnd.uniform(2, 45)
                z = camera[2] + rnd.uniform(15, 260)
                gl_color((160, 220, 245), alpha=120)
                gl.glVertex3f(x, y, z)
                gl.glVertex3f(x + 22, y + 2.5, z - 14)
            gl.glEnd()
        elif terrain == "haze":
            gl.glEnable(gl.GL_BLEND)
            gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            for i in range(18):
                rnd = _deterministic_rng(seed, i, int(float(state["t_current"])))
                x = camera[0] + rnd.uniform(-120, 120)
                z = camera[2] + rnd.uniform(40, 260)
                y = _terrain_height(x, z, terrain)
                draw_cone(x, y, z, rnd.uniform(0.8, 2.2), rnd.uniform(7.0, 18.0), 5, (255, 132, 58))
            gl.glDisable(gl.GL_BLEND)

    @window.event
    def on_key_press(symbol: int, modifiers: int) -> None:
        if symbol == key.ESCAPE:
            pyglet.app.exit()
            window.close()
        elif symbol == key.F11:
            try:
                window.set_fullscreen(not window.fullscreen)
            except Exception:
                pass
        elif symbol == key.T:
            state["telescope"] = not bool(state["telescope"])
            state["zoom"] = 5.0 if bool(state["telescope"]) else 1.0
        elif symbol == key.SPACE:
            state["paused"] = not bool(state["paused"])
        elif symbol == key.F1:
            state["show_help"] = not bool(state["show_help"])
        elif symbol in {getattr(key, "PLUS", None), getattr(key, "NUM_ADD", None), getattr(key, "_2", None)}:
            state["speed"] = min(64.0, float(state["speed"]) * 2.0)
        elif symbol in {getattr(key, "MINUS", None), getattr(key, "NUM_SUBTRACT", None), getattr(key, "_1", None)}:
            state["speed"] = max(0.125, float(state["speed"]) * 0.5)
        elif symbol == key.M:
            state["exclusive_mouse"] = not bool(state["exclusive_mouse"])
            try:
                window.set_exclusive_mouse(bool(state["exclusive_mouse"]))
            except Exception:
                pass

    @window.event
    def on_mouse_motion(x: int, y: int, dx: int, dy: int) -> None:
        sensitivity = 0.115 / max(1.0, float(state["zoom"]) ** 0.25)
        state["yaw"] = (float(state["yaw"]) + dx * sensitivity) % 360.0
        state["pitch"] = max(-86.0, min(86.0, float(state["pitch"]) + dy * sensitivity))

    @window.event
    def on_mouse_scroll(x: int, y: int, scroll_x: float, scroll_y: float) -> None:
        state["zoom"] = max(1.0, min(9.0, float(state["zoom"]) * (1.0 + scroll_y * 0.12)))
        state["telescope"] = float(state["zoom"]) > 2.4

    def update(dt: float) -> None:
        if not bool(state["paused"]):
            span = max(1e-6, t_max - t_min)
            state["t_current"] = t_min + ((float(state["t_current"]) - t_min + dt * float(state["speed"]) * 0.25) % span)
        yaw_rad = math.radians(float(state["yaw"]))
        forward = (math.sin(yaw_rad), math.cos(yaw_rad))
        right = (math.cos(yaw_rad), -math.sin(yaw_rad))
        move_x = 0.0
        move_z = 0.0
        if keys[key.W] or keys[key.UP]:
            move_x += forward[0]; move_z += forward[1]
        if keys[key.S] or keys[key.DOWN]:
            move_x -= forward[0]; move_z -= forward[1]
        if keys[key.D] or keys[key.RIGHT]:
            move_x += right[0]; move_z += right[1]
        if keys[key.A] or keys[key.LEFT]:
            move_x -= right[0]; move_z -= right[1]
        length = math.hypot(move_x, move_z)
        if length > 0:
            speed = 34.0 * (1.8 if keys[key.LSHIFT] or keys[key.RSHIFT] else 1.0)
            state["x"] = float(state["x"]) + (move_x / length) * speed * dt
            state["z"] = float(state["z"]) + (move_z / length) * speed * dt
            state["walking_phase"] = float(state["walking_phase"]) + dt * speed * 0.45

    @window.event
    def on_draw() -> None:
        gl.glViewport(0, 0, window.width, window.height)
        reset_scene_gl_state(for_2d=False)
        gl.glClearColor(sky_top[0]/255.0, sky_top[1]/255.0, sky_top[2]/255.0, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        draw_sky_dome()
        set_projection_3d()
        reset_scene_gl_state(for_2d=False)
        try:
            gl.glEnable(gl.GL_MULTISAMPLE)
        except Exception:
            pass
        camera = apply_camera()
        draw_stars(camera)
        draw_ground()
        draw_props()
        draw_environment_effects(camera)
        draw_target(camera)
        reset_scene_gl_state(for_2d=True)
        set_projection_2d()
        sample = _interpolated_sample(samples, float(state["t_current"]))
        fps_label.text = (
            f"Pyglet/OpenGL Play Scenario | WASD move, mouse look, wheel zoom, T telescope, F1 help, Esc quit | "
            f"t={sample.get('t_hours', 0.0):+.2f} h  dist={format_number(sample.get('distance_km', 0.0), 0)} km  "
            f"yaw={float(state['yaw']):.0f} pitch={float(state['pitch']):.0f} zoom={float(state['zoom']):.1f}x"
        )
        fps_label.draw()
        if bool(state["show_help"]):
            help_label.text = (
                "This is a playful educational OpenGL scene, not a real ephemeris renderer.\n"
                "The marker follows synthetic CAD-derived sky-direction samples from the local simulation.\n"
                "The terrain, trees, rocks, colors and textures are procedurally generated approximations.\n"
                "For real observing or mission work use JPL Horizons/SPICE, lighting, local geography and mission ephemerides.\n"
                "Controls: WASD/arrow keys, mouse look, wheel zoom, T telescope, Space pause, 1/2 speed, M mouse capture, Esc quit."
            )
            help_label.draw()

    pyglet.clock.schedule_interval(update, 1.0 / 60.0)
    try:
        pyglet.app.run()
    finally:
        try:
            window.set_exclusive_mouse(False)
        except Exception:
            pass
    return 0


def run_pyglet_scenario(scenario_path: Path) -> int:
    try:
        return _run_pyglet_scenario_impl(scenario_path)
    except SystemExit:
        raise
    except Exception:
        print("Pyglet/OpenGL scene failed with an unhandled exception; falling back if possible.")
        print(traceback.format_exc())
        return 5

def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("Usage: python -m jpl_cad_ollama_explorer.game_scenario <scenario.json>")
        return 2
    result = run_pyglet_scenario(Path(args[0]))
    if result in {3, 4, 5}:
        print("Falling back to legacy Pygame software scene.")
        return run_pygame_scenario(Path(args[0]))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
