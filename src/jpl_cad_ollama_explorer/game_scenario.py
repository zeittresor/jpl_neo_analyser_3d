# source: https://github.com/zeittresor
from __future__ import annotations

import json
import math
import random
import sys
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
            "scene_name": "Earth forest overlook",
            "sky_top": [4, 12, 30],
            "sky_bottom": [17, 34, 58],
            "ground": [16, 36, 22],
            "ground_far": [31, 62, 34],
            "accent": [105, 210, 255],
            "fog": [12, 18, 20],
            "terrain": "forest",
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
    """Write a small JSON scenario for the optional Pygame education mode.

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
            "Educational game-like visualization only: synthetic CAD-derived sky direction, not a real landscape, "
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
    sky_h = int(h * 0.62)
    for y in range(sky_h):
        t = y / max(1, sky_h - 1)
        pygame.draw.line(screen, _lerp_color(top, bottom, t), (0, y), (w, y))


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
    horizon = int(h * 0.62)
    ground = scene.get("ground", [45, 45, 45])
    far = scene.get("ground_far", [90, 90, 90])
    for y in range(horizon, h):
        t = (y - horizon) / max(1, h - horizon)
        pygame.draw.line(screen, _lerp_color(far, ground, t), (0, y), (w, y))

    terrain = scene.get("terrain", "rocky")
    # Parallax hills.  This is deliberately stylized and deterministic rather than realistic.
    for layer, amp, base_offset, color_mul in [(0, 38, 0, 0.72), (1, 72, 20, 0.92)]:
        points: list[tuple[int, int]] = []
        phase = math.radians(yaw * (0.45 + layer * 0.15)) + player_x * 0.004 + player_z * 0.002 + layer * 1.7
        for x in range(-20, w + 21, 20):
            n = math.sin(x * 0.012 + phase) + 0.45 * math.sin(x * 0.027 + phase * 1.8)
            y = int(horizon + base_offset + amp * (0.6 + 0.5 * n))
            points.append((x, y))
        points.extend([(w + 20, h), (-20, h)])
        col = tuple(max(0, min(255, int(c * color_mul))) for c in (far if layer == 0 else ground))
        pygame.draw.polygon(screen, col, points)

    if terrain == "forest":
        random.seed(rng_seed)
        for i in range(70):
            world = i * 137.0
            x = int((world - player_x * 0.9 + yaw * 3.2) % (w + 140) - 70)
            y = int(horizon + 40 + (i * 53) % max(1, h - horizon - 55))
            scale = 0.45 + (y - horizon) / max(1, h - horizon) * 1.2
            trunk_h = int(22 * scale)
            crown = int(18 * scale)
            pygame.draw.rect(screen, (52, 34, 21), (x - 2, y - trunk_h, 4, trunk_h))
            pygame.draw.polygon(screen, (16, 71, 37), [(x, y - trunk_h - crown), (x - crown, y - trunk_h + crown), (x + crown, y - trunk_h + crown)])
    elif terrain == "haze":
        random.seed(rng_seed + 77)
        for i in range(34):
            x = int((i * 197 - player_x * 0.45 + yaw * 1.4) % (w + 120) - 60)
            y = int(horizon + 35 + (i * 43) % max(1, h - horizon - 60))
            r = 8 + (i * 11) % 36
            pygame.draw.ellipse(screen, (min(255, ground[0] + 50), min(255, ground[1] + 25), max(0, ground[2] - 8)), (x - r, y - r // 3, r * 2, r // 2), 1)
    elif terrain == "ice_wind":
        random.seed(rng_seed + 143)
        for i in range(42):
            x = int((i * 211 - player_x * 0.6 + yaw * 2.4) % (w + 140) - 70)
            y = int(horizon + 35 + (i * 67) % max(1, h - horizon - 70))
            length = 18 + (i * 5) % 45
            col = (150, 195, 220)
            pygame.draw.line(screen, col, (x, y), (x + length, y - 4), 1)
    elif terrain in {"craters", "asteroid", "rocky", "gas_giant_moon"}:
        random.seed(rng_seed + 99)
        for i in range(28):
            x = int((i * 233 - player_x * 0.55 + yaw * 2.0) % (w + 100) - 50)
            y = int(horizon + 65 + (i * 71) % max(1, h - horizon - 80))
            r = 5 + (i * 7) % 24
            pygame.draw.ellipse(screen, (max(0, ground[0] - 35), max(0, ground[1] - 35), max(0, ground[2] - 35)), (x - r * 2, y - r // 2, r * 4, r))
            pygame.draw.ellipse(screen, (min(255, ground[0] + 18), min(255, ground[1] + 18), min(255, ground[2] + 18)), (x - r * 2, y - r // 2, r * 4, r), 1)


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
        _draw_ground(screen, scene, yaw, player_x, player_z, seed)
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


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("Usage: python -m jpl_cad_ollama_explorer.game_scenario <scenario.json>")
        return 2
    return run_pygame_scenario(Path(args[0]))


if __name__ == "__main__":
    raise SystemExit(main())
