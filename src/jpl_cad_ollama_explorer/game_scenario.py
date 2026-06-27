# source: https://github.com/zeittresor
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import random
import sys
import traceback
import time
import wave
from pathlib import Path
from typing import Any

from .cad_models import CadRecord
from .constants import BODY_DISPLAY, BODY_RADIUS_KM
from .simulator import SimulationResult
from .surface_view import _neo_view, _sanitize_name, _select_path, _select_time_window, _surface_sky


def _scenario_log(level: str, message: str) -> None:
    """Write a timestamped Play Scenario diagnostic line to stdout.

    The main GUI redirects stdout/stderr into output/logs/play_scenario_*.txt, so every
    renderer decision, GPU/backend detail and fallback reason becomes visible in the app Log tab
    and in the persistent scenario log file.
    """
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"[SCENARIO {level.upper()}] {stamp} | {message}", flush=True)


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
    """Write a small JSON scenario for the optional Panda3D education mode.

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
        "schema": "jpl_cad_ollama_explorer.panda3d_scenario.v2",
        "visual_style": "stylized_low_poly_education_scene_panda3d",
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
            "jump": "Space",
            "pause": "P",
            "target_track": "C",
            "journal": "J",
            "time_speed": "1/2 or +/-",
            "fullscreen_toggle": "F11",
            "screenshot": "Home / Pos1",
            "quit": "Esc",
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


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _rgb(scene: dict[str, Any], key: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    value = scene.get(key, fallback)
    try:
        return (int(value[0]), int(value[1]), int(value[2]))
    except Exception:
        return fallback


def _rgbf(color: tuple[int, int, int] | list[int], alpha: float = 1.0) -> tuple[float, float, float, float]:
    return (_clamp(float(color[0]) / 255.0, 0.0, 1.0), _clamp(float(color[1]) / 255.0, 0.0, 1.0), _clamp(float(color[2]) / 255.0, 0.0, 1.0), alpha)


def _shade(color: tuple[int, int, int], delta: int) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c) + delta)) for c in color)  # type: ignore[return-value]


def _configure_panda(render_device: str, windowed: bool = False) -> None:
    """Apply Panda3D config before ShowBase is imported/created."""
    from panda3d.core import loadPrcFileData

    device = (render_device or "auto").lower()
    if device in {"software", "cpu", "tinydisplay"}:
        display = "tinydisplay"
        aux = "pandagl"
        device_note = "TinyPanda CPU/software renderer requested."
    elif device in {"directx", "dx", "d3d", "d3d9"}:
        display = "pandadx9"
        aux = "pandagl tinydisplay"
        device_note = "DirectX 9 requested, with OpenGL/software as Panda3D auxiliary fallbacks when available."
    else:
        display = "pandagl"
        aux = "tinydisplay"
        device_note = "OpenGL hardware renderer requested. Exact NVIDIA/Radeon/Intel adapter choice is controlled by Windows/GPU driver settings."

    fullscreen = "#f" if windowed else "#t"
    prc = f"""
        window-title JPL CAD Ollama Explorer - Panda3D Play Scenario
        load-display {display}
        aux-display {aux}
        fullscreen {fullscreen}
        win-size 1280 720
        sync-video #t
        show-frame-rate-meter #t
        framebuffer-multisample #t
        multisamples 4
        textures-power-2 none
        texture-anisotropic-degree 4
        gl-check-errors #f
        notify-level warning
        default-directnotify-level warning
    """
    loadPrcFileData("jpl-cad-panda3d-scenario", prc)
    _scenario_log("INFO", f"Panda3D configuration applied: load-display={display}; aux-display={aux}; render_device={device}; {device_note}")


def _prepare_shader_cache(cache_dir: Path | None, mode: str = "auto") -> tuple[Path | None, Path | None]:
    if mode == "off":
        _scenario_log("INFO", "Shader cache disabled by option.")
        return None, None
    if cache_dir is None:
        _scenario_log("WARN", "Shader cache has no directory; shader source cache disabled.")
        return None, None
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        vertex_path = cache_dir / "panda3d_low_poly_vertex_120.glsl"
        fragment_path = cache_dir / "panda3d_low_poly_fragment_120.glsl"
        manifest_path = cache_dir / "shader_cache_manifest.json"
        created: list[str] = []
        if not vertex_path.exists():
            vertex_path.write_text(
                "// JPL CAD Ollama Explorer - Panda3D reusable low-poly vertex shader\n"
                "#version 120\n"
                "uniform mat4 p3d_ModelViewProjectionMatrix;\n"
                "attribute vec4 p3d_Vertex;\n"
                "attribute vec4 p3d_Color;\n"
                "varying vec4 v_color;\n"
                "void main() {\n"
                "    v_color = p3d_Color;\n"
                "    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;\n"
                "}\n",
                encoding="utf-8",
            )
            created.append(vertex_path.name)
        if not fragment_path.exists():
            fragment_path.write_text(
                "// JPL CAD Ollama Explorer - Panda3D reusable low-poly fragment shader\n"
                "#version 120\n"
                "varying vec4 v_color;\n"
                "void main() {\n"
                "    gl_FragColor = v_color;\n"
                "}\n",
                encoding="utf-8",
            )
            created.append(fragment_path.name)
        manifest = {
            "schema": "jpl_cad_ollama_explorer.panda3d_shader_cache.v1",
            "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mode": mode,
            "active_renderer": "Panda3D",
            "note": "The files are stable GLSL 1.20 sources. GPU binary caching is controlled by the graphics driver/Panda3D runtime.",
            "files": [vertex_path.name, fragment_path.name],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        action = "created" if created else "reused"
        _scenario_log("INFO", f"Shader cache {action}: {cache_dir} ({', '.join(created) if created else 'existing files'})")
        return vertex_path, fragment_path
    except Exception as exc:
        _scenario_log("WARN", f"Shader cache preparation failed: {exc}")
        return None, None


def _terrain_height(x: float, y: float, terrain: str) -> float:
    base = math.sin(x * 0.055) * 0.9 + math.cos(y * 0.047) * 0.8 + math.sin((x + y) * 0.025) * 0.6
    if terrain in {"asteroid", "craters", "rocky"}:
        return base * 1.15 + math.sin(x * 0.19 + y * 0.03) * 0.35
    if terrain in {"red_hills", "gas_giant_moon"}:
        return base * 1.55 + math.sin(y * 0.018) * 1.8
    if terrain == "ice_wind":
        return base * 0.75 + math.sin(x * 0.03) * 0.45
    if terrain == "haze":
        return base * 0.55
    return base * 0.9


def _ambient_audio_profile(terrain: str) -> dict[str, float]:
    """Return small procedural ambient-audio parameters for the current scene type."""
    if terrain == "forest":
        return {"volume": 0.38, "wind": 0.20, "rumble": 0.05, "chirps": 1.0}
    if terrain in {"red_hills", "haze"}:
        return {"volume": 0.34, "wind": 0.42, "rumble": 0.13, "chirps": 0.0}
    if terrain in {"ice_wind", "gas_giant_moon"}:
        return {"volume": 0.32, "wind": 0.50, "rumble": 0.10, "chirps": 0.0}
    if terrain in {"asteroid", "craters"}:
        return {"volume": 0.25, "wind": 0.07, "rumble": 0.18, "chirps": 0.0}
    return {"volume": 0.30, "wind": 0.24, "rumble": 0.10, "chirps": 0.0}


def _write_ambient_wav(path: Path, terrain: str, seed_text: str) -> bool:
    """Generate a tiny looping mono WAV ambience without external dependencies."""
    try:
        if path.exists() and path.stat().st_size > 4096:
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        profile = _ambient_audio_profile(terrain)
        rng = random.Random(int(abs(hash((terrain, seed_text))) & 0xFFFFFFFF))
        sample_rate = 22050
        seconds = 8.0
        total = int(sample_rate * seconds)
        samples = bytearray()
        smooth = 0.0
        chirp_phase = 0.0
        chirp_timer = rng.uniform(0.4, 1.6)
        chirp_freq = 1200.0
        for i in range(total):
            t = i / sample_rate
            smooth = smooth * 0.986 + rng.uniform(-1.0, 1.0) * 0.014
            wind = smooth * float(profile["wind"])
            rumble = math.sin(math.tau * 42.0 * t + 0.7 * math.sin(t * 0.8)) * float(profile["rumble"])
            tone = math.sin(math.tau * 115.0 * t) * 0.025
            chirp = 0.0
            if profile.get("chirps", 0.0) > 0.0:
                chirp_timer -= 1.0 / sample_rate
                if chirp_timer <= 0.0:
                    chirp_timer = rng.uniform(0.9, 2.4)
                    chirp_phase = 0.16
                    chirp_freq = rng.uniform(1250.0, 2450.0)
                if chirp_phase > 0.0:
                    chirp_phase -= 1.0 / sample_rate
                    env = max(0.0, min(1.0, chirp_phase / 0.16))
                    chirp = math.sin(math.tau * chirp_freq * t) * env * 0.13
            value = max(-0.96, min(0.96, wind + rumble + tone + chirp))
            ivalue = int(value * 32767)
            samples.extend(int(ivalue).to_bytes(2, byteorder="little", signed=True))
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(bytes(samples))
        return True
    except Exception as exc:
        _scenario_log("WARN", f"Ambient audio generation failed: {exc}")
        return False


class PandaScenarioApp:  # pragma: no cover - interactive renderer
    def __init__(self, scenario_path: Path, render_device: str, shader_cache_dir: Path, shader_cache: str) -> None:
        from direct.gui.OnscreenText import OnscreenText
        from direct.showbase.ShowBase import ShowBase
        from panda3d.core import (
            AmbientLight,
            AntialiasAttrib,
            CardMaker,
            DirectionalLight,
            Filename,
            Fog,
            Geom,
            GeomNode,
            GeomTriangles,
            GeomVertexData,
            GeomVertexFormat,
            GeomVertexWriter,
            LColor,
            NodePath,
            Point3,
            Shader,
            TransparencyAttrib,
            Vec3,
            WindowProperties,
        )
        from panda3d.core import KeyboardButton

        self._panda = {
            "OnscreenText": OnscreenText,
            "ShowBase": ShowBase,
            "AmbientLight": AmbientLight,
            "AntialiasAttrib": AntialiasAttrib,
            "CardMaker": CardMaker,
            "DirectionalLight": DirectionalLight,
            "Filename": Filename,
            "Fog": Fog,
            "Geom": Geom,
            "GeomNode": GeomNode,
            "GeomTriangles": GeomTriangles,
            "GeomVertexData": GeomVertexData,
            "GeomVertexFormat": GeomVertexFormat,
            "GeomVertexWriter": GeomVertexWriter,
            "LColor": LColor,
            "NodePath": NodePath,
            "Point3": Point3,
            "Shader": Shader,
            "TransparencyAttrib": TransparencyAttrib,
            "Vec3": Vec3,
            "WindowProperties": WindowProperties,
            "KeyboardButton": KeyboardButton,
        }

        self.scenario_path = scenario_path
        self.scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        self.scene = dict(self.scenario.get("scene", {}))
        self.samples = list(self.scenario.get("samples", []))
        if not self.samples:
            raise ValueError("Scenario JSON contains no samples; cannot animate target marker.")

        self.base = ShowBase()
        self.base.disableMouse()
        self.render = self.base.render
        # Panda3D exposes two camera-related NodePaths:
        # - base.camera: the transform node normally moved through the world
        # - base.cam: the actual Camera node that owns the Lens
        # Accessing getLens() on base.camera fails on some Panda3D builds because
        # it is a ModelNode, not a Camera. Keep both references explicit.
        self.camera = self.base.camera
        self.cam_node = self.base.cam
        self.loader = self.base.loader
        self.task_mgr = self.base.taskMgr
        self.render_device = render_device
        self.shader_cache_dir = shader_cache_dir
        self.shader_cache = shader_cache
        self.shader = None
        self.output_dir = scenario_path.parent.parent if scenario_path.parent.name.lower() == "visualizations" else scenario_path.parent
        self.screenshot_dir = self.output_dir / "screenshots"
        self.audio_dir = self.output_dir / "audio"
        self.ambient_sound = None

        self.yaw = 0.0
        self.pitch = 0.0
        self.speed = 10.0
        self.time_speed = 1.0
        self.paused = False
        self.telescope = False
        self.elapsed = 0.0
        self.player_x = 0.0
        self.player_y = -10.0
        # One Panda3D world unit is treated as roughly one metre. Keep the camera at
        # realistic standing eye height above terrain instead of placing it at floor level.
        self.eye_height = 1.80
        self.fullscreen = True
        self.last_centered = False
        self.player_radius = 0.42
        self.colliders: list[tuple[float, float, float, str]] = []
        self.jump_offset = 0.0
        self.vertical_velocity = 0.0
        self.grounded = True
        self.track_target = False
        self.journal_visible = False
        self.sky_np = None

        self._log_driver_info()
        self._setup_window()
        self._setup_lighting_and_fog()
        self._setup_shaders()
        self._build_world()
        self._setup_ambient_audio()
        self._build_hud()
        self._install_controls()
        self._warm_renderer()

    def _log_driver_info(self) -> None:
        win = getattr(self.base, "win", None)
        gsg = win.getGsg() if win else None
        if gsg is None:
            _scenario_log("WARN", "Panda3D window has no GraphicsStateGuardian; driver information unavailable.")
            return
        def call(name: str) -> str:
            try:
                method = getattr(gsg, name)
                return str(method())
            except Exception:
                return "unknown"
        _scenario_log("INFO", "ENGINE_SELECTED=panda3d")
        _scenario_log("INFO", f"Panda3D platform: Python={sys.version.split()[0]}; OS={platform.platform()}")
        _scenario_log("INFO", f"Panda3D GSG vendor={call('getDriverVendor')}; renderer={call('getDriverRenderer')}; version={call('getDriverVersion')}")
        _scenario_log("INFO", f"Panda3D GSG shader-model={call('getShaderModel')}; supports-basic-shaders={call('getSupportsBasicShaders')}")

    def _camera_lens(self):
        lens = getattr(self.base, "camLens", None)
        if lens is not None:
            return lens
        return self.cam_node.node().getLens()

    def _setup_window(self) -> None:
        WindowProperties = self._panda["WindowProperties"]
        props = WindowProperties()
        props.setTitle(f"JPL CAD Play Scenario - {self.scenario.get('object_name', '')}")
        props.setCursorHidden(True)
        props.setFullscreen(True)
        self.base.win.requestProperties(props)
        self.base.setFrameRateMeter(True)
        lens = self._camera_lens()
        lens.setFov(74)
        lens.setNearFar(0.035, 650.0)
        sky = _rgb(self.scene, "sky_top", (4, 8, 18))
        self.base.win.setClearColor(_rgbf(sky, 1.0))
        _scenario_log("INFO", f"Window configured: fullscreen=True; eye_height_m={self.eye_height:.2f}; near_clip=0.035; screenshots={self.screenshot_dir}")

    def _setup_lighting_and_fog(self) -> None:
        Vec3 = self._panda["Vec3"]
        AmbientLight = self._panda["AmbientLight"]
        DirectionalLight = self._panda["DirectionalLight"]
        Fog = self._panda["Fog"]

        ambient = AmbientLight("ambient")
        ambient.setColor((0.42, 0.43, 0.48, 1.0))
        self.render.setLight(self.render.attachNewNode(ambient))

        sun = DirectionalLight("sun")
        sun.setColor((0.92, 0.88, 0.78, 1.0))
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(-35, -55, 0)
        self.render.setLight(sun_np)

        fog_rgb = _rgb(self.scene, "fog", _rgb(self.scene, "sky_bottom", (28, 36, 60)))
        fog = Fog("distance_fog")
        # Panda3D's Fog.setColor overload accepts either a color object or RGB floats.
        # Passing RGBA as four separate floats raises on some Panda3D builds:
        # TypeError: set_color() takes 2 or 4 arguments (5 given).
        # Keep fog RGB-only; alpha is not meaningful for exponential scene fog anyway.
        fog.setColor(*_rgbf(fog_rgb, 1.0)[:3])
        fog.setExpDensity(0.012)
        self.render.setFog(fog)
        self.render.setAntialias(self._panda["AntialiasAttrib"].MAuto)
        _scenario_log("INFO", "Panda3D lighting/fog setup completed.")

    def _setup_shaders(self) -> None:
        Shader = self._panda["Shader"]
        vertex_path, fragment_path = _prepare_shader_cache(self.shader_cache_dir, self.shader_cache)
        if vertex_path is None or fragment_path is None:
            _scenario_log("INFO", "Shader source cache not active; Panda3D fixed/auto pipeline remains available.")
            return
        try:
            self.shader = Shader.load(Shader.SL_GLSL, str(vertex_path), str(fragment_path))
            _scenario_log("INFO", f"Shader loaded and will be bound to low-poly geometry: {vertex_path.name}, {fragment_path.name}")
        except Exception as exc:
            self.shader = None
            _scenario_log("WARN", f"Shader load failed; continuing with Panda3D default hardware pipeline: {exc}")

    def _make_geom_node(self, name: str, vertices: list[tuple[float, float, float]], tris: list[tuple[int, int, int]], colors: list[tuple[float, float, float, float]]):
        GeomVertexFormat = self._panda["GeomVertexFormat"]
        GeomVertexData = self._panda["GeomVertexData"]
        GeomVertexWriter = self._panda["GeomVertexWriter"]
        GeomTriangles = self._panda["GeomTriangles"]
        Geom = self._panda["Geom"]
        GeomNode = self._panda["GeomNode"]
        Vec3 = self._panda["Vec3"]

        fmt = GeomVertexFormat.getV3n3c4()
        vdata = GeomVertexData(name, fmt, Geom.UHStatic)
        vdata.setNumRows(len(vertices))
        vw = GeomVertexWriter(vdata, "vertex")
        nw = GeomVertexWriter(vdata, "normal")
        cw = GeomVertexWriter(vdata, "color")
        for idx, (x, y, z) in enumerate(vertices):
            vw.addData3f(float(x), float(y), float(z))
            nw.addData3f(0.0, 0.0, 1.0)
            col = colors[idx] if idx < len(colors) else (1.0, 1.0, 1.0, 1.0)
            cw.addData4f(*col)
        prim = GeomTriangles(Geom.UHStatic)
        for a, b, c in tris:
            prim.addVertices(int(a), int(b), int(c))
        prim.closePrimitive()
        geom = Geom(vdata)
        geom.addPrimitive(prim)
        node = GeomNode(name)
        node.addGeom(geom)
        return node

    def _build_world(self) -> None:
        self._build_sky_dome()
        self.terrain_np = self._build_terrain()
        self._scatter_props()
        self.target_np = self._build_target_marker()
        self._build_first_person_body()
        self._update_camera(0.0)

    def _build_sky_dome(self) -> None:
        """Build one continuous camera-centred sky dome.

        Earlier builds used several translucent vertical sky cards. They looked like cube-map seams
        and could cover the terrain in the foreground. This dome is opaque, drawn in the background
        bin and re-centred on the camera every frame, so it behaves like sky instead of an overlay.
        """
        sky_top = _rgb(self.scene, "sky_top", (5, 8, 22))
        sky_bottom = _rgb(self.scene, "sky_bottom", (28, 38, 70))
        radius = 520.0
        rings = 18
        segments = 48
        vertices: list[tuple[float, float, float]] = []
        colors: list[tuple[float, float, float, float]] = []
        for r in range(rings + 1):
            phi = math.pi * r / rings
            z_norm = math.cos(phi)
            ring_radius = math.sin(phi) * radius
            z = z_norm * radius
            t = _clamp((z_norm + 0.18) / 1.18, 0.0, 1.0)
            col = tuple(int(_lerp(sky_bottom[j], sky_top[j], t)) for j in range(3))
            for seg in range(segments):
                theta = math.tau * seg / segments
                vertices.append((math.cos(theta) * ring_radius, math.sin(theta) * ring_radius, z))
                colors.append(_rgbf(col, 1.0))
        tris: list[tuple[int, int, int]] = []
        for r in range(rings):
            for seg in range(segments):
                a = r * segments + seg
                b = r * segments + ((seg + 1) % segments)
                c = (r + 1) * segments + seg
                d = (r + 1) * segments + ((seg + 1) % segments)
                # Reversed winding because the camera is inside the dome.
                tris.append((a, b, c))
                tris.append((b, d, c))
        node = self._make_geom_node("sky_dome", vertices, tris, colors)
        sky = self.render.attachNewNode(node)
        sky.setLightOff(1)
        sky.setDepthWrite(False)
        sky.setDepthTest(False)
        sky.setTwoSided(True)
        sky.setBin("background", 0)
        self.sky_np = sky
        _scenario_log("INFO", "Continuous sky dome built; legacy translucent sky cards/cubemap-like seams disabled.")

    def _build_terrain(self):
        size = 210.0
        steps = 96
        step = size / steps
        terrain = str(self.scene.get("terrain", "rocky"))
        ground = _rgb(self.scene, "ground", (80, 80, 70))
        far = _rgb(self.scene, "ground_far", _shade(ground, 35))
        vertices: list[tuple[float, float, float]] = []
        colors: list[tuple[float, float, float, float]] = []
        for iy in range(steps + 1):
            y = -size / 2.0 + iy * step
            for ix in range(steps + 1):
                x = -size / 2.0 + ix * step
                z = _terrain_height(x, y, terrain)
                dist = _clamp(math.sqrt(x * x + y * y) / (size * 0.65), 0.0, 1.0)
                shade = 0.78 + 0.22 * math.sin((x + 3.0 * y) * 0.03)
                col = tuple(int(_lerp(ground[j], far[j], dist) * shade) for j in range(3))
                vertices.append((x, y, z))
                colors.append(_rgbf(col, 1.0))
        tris: list[tuple[int, int, int]] = []
        row = steps + 1
        for iy in range(steps):
            for ix in range(steps):
                a = iy * row + ix
                b = a + 1
                c = a + row
                d = c + 1
                tris.append((a, c, b))
                tris.append((b, c, d))
        node = self._make_geom_node("terrain_mesh", vertices, tris, colors)
        np = self.render.attachNewNode(node)
        np.setTwoSided(True)
        np.setDepthWrite(True)
        np.setDepthTest(True)
        if self.shader is not None:
            np.setShader(self.shader)
        _scenario_log("INFO", f"Terrain mesh built: vertices={len(vertices)}; triangles={len(tris)}; shader={'yes' if self.shader is not None else 'no'}")
        return np

    def _make_cone(self, name: str, radius: float, height: float, segments: int, color: tuple[int, int, int]):
        vertices = [(0.0, 0.0, height)]
        colors = [_rgbf(_shade(color, 25), 1.0)]
        for i in range(segments):
            a = math.tau * i / segments
            vertices.append((math.cos(a) * radius, math.sin(a) * radius, 0.0))
            colors.append(_rgbf(color, 1.0))
        tris = []
        for i in range(segments):
            tris.append((0, 1 + i, 1 + ((i + 1) % segments)))
        node = self._make_geom_node(name, vertices, tris, colors)
        np = self._panda["NodePath"](node)
        if self.shader is not None:
            np.setShader(self.shader)
        return np

    def _make_box(self, name: str, sx: float, sy: float, sz: float, color: tuple[int, int, int]):
        x, y, z = sx / 2.0, sy / 2.0, sz / 2.0
        vertices = [
            (-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
            (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z),
        ]
        tris = [(0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 4, 5), (0, 5, 1), (1, 5, 6), (1, 6, 2), (2, 6, 7), (2, 7, 3), (3, 7, 4), (3, 4, 0)]
        colors = [_rgbf(color, 1.0)] * 8
        node = self._make_geom_node(name, vertices, tris, colors)
        np = self._panda["NodePath"](node)
        if self.shader is not None:
            np.setShader(self.shader)
        return np

    def _make_sphere(self, name: str, radius: float, color: tuple[int, int, int], rings: int = 10, segments: int = 18):
        vertices: list[tuple[float, float, float]] = []
        colors: list[tuple[float, float, float, float]] = []
        for r in range(rings + 1):
            phi = math.pi * r / rings
            for s in range(segments):
                theta = math.tau * s / segments
                x = math.sin(phi) * math.cos(theta) * radius
                y = math.sin(phi) * math.sin(theta) * radius
                z = math.cos(phi) * radius
                vertices.append((x, y, z))
                light = 0.72 + 0.28 * max(0.0, math.cos(theta - 0.7) * math.sin(phi))
                colors.append(_rgbf(tuple(int(c * light) for c in color), 1.0))
        tris: list[tuple[int, int, int]] = []
        for r in range(rings):
            for s in range(segments):
                a = r * segments + s
                b = r * segments + ((s + 1) % segments)
                c = (r + 1) * segments + s
                d = (r + 1) * segments + ((s + 1) % segments)
                tris.append((a, c, b))
                tris.append((b, c, d))
        node = self._make_geom_node(name, vertices, tris, colors)
        np = self._panda["NodePath"](node)
        if self.shader is not None:
            np.setShader(self.shader)
        return np

    def _scatter_props(self) -> None:
        rng = random.Random(int(abs(hash(str(self.scenario.get("object_name", "scenario")))) & 0xFFFFFFFF))
        terrain = str(self.scene.get("terrain", "rocky"))
        accent = _rgb(self.scene, "accent", (160, 210, 255))
        ground = _rgb(self.scene, "ground", (80, 80, 70))
        self.colliders = []
        count = 90 if terrain == "forest" else 55
        for idx in range(count):
            angle = rng.random() * math.tau
            dist = rng.uniform(14.0, 92.0)
            x = math.cos(angle) * dist
            y = math.sin(angle) * dist
            z = _terrain_height(x, y, terrain)
            if terrain == "forest" and rng.random() < 0.78:
                trunk_h = rng.uniform(1.6, 2.8)
                crown_r = rng.uniform(0.9, 1.6)
                trunk = self._make_box(f"trunk_{idx}", 0.35, 0.35, trunk_h, _shade(ground, -35))
                trunk.reparentTo(self.render)
                trunk.setPos(x, y, z + trunk_h * 0.5)
                self.colliders.append((x, y, max(0.55, crown_r * 0.45), f"tree_{idx}"))
                crown = self._make_cone(f"crown_{idx}", crown_r, rng.uniform(2.4, 4.0), 7, _shade(ground, 22))
                crown.reparentTo(self.render)
                crown.setPos(x, y, z + 1.75)
                crown.setH(rng.uniform(0, 360))
            else:
                rock_r = rng.uniform(0.35, 1.1)
                rock = self._make_cone(f"rock_{idx}", rock_r, rng.uniform(0.5, 1.9), 6, _shade(ground if rng.random() < 0.7 else accent, -10))
                rock.reparentTo(self.render)
                rock.setPos(x, y, z)
                self.colliders.append((x, y, max(0.35, rock_r * 0.9), f"rock_{idx}"))
                rock.setHpr(rng.uniform(0, 360), rng.uniform(-6, 6), rng.uniform(-6, 6))
        _scenario_log("INFO", f"Scene props generated: count={count}; terrain={terrain}; collision_volumes={len(self.colliders)}")

    def _build_target_marker(self):
        accent = _rgb(self.scene, "accent", (160, 210, 255))
        NodePath = self._panda["NodePath"]
        root = NodePath("target_marker_root")
        root.reparentTo(self.render)
        radius = 1.9 if self.scenario.get("mode") != "neo" else 5.5
        core = self._make_sphere("target_marker_core", radius, accent, rings=12, segments=24)
        core.reparentTo(root)
        core.setLightOff(1)
        core.setFogOff(1)
        halo_color = _shade(accent, 45)
        for idx in range(8):
            angle = math.tau * idx / 8.0
            bead = self._make_sphere(f"target_marker_halo_{idx}", max(0.18, radius * 0.16), halo_color, rings=6, segments=10)
            bead.reparentTo(root)
            bead.setPos(math.cos(angle) * radius * 1.7, math.sin(angle) * radius * 1.7, 0.0)
            bead.setLightOff(1)
            bead.setFogOff(1)
        stem = self._make_box("target_marker_vertical_beacon", 0.10, 0.10, radius * 4.0, halo_color)
        stem.reparentTo(root)
        stem.setPos(0, 0, radius * 2.0)
        stem.setLightOff(1)
        stem.setFogOff(1)
        root.setFogOff(1)
        root.setColorScale(1.25, 1.25, 1.25, 1.0)
        _scenario_log("INFO", "Target marker built as bright beacon/halo so the CAD object direction remains visible in PTS.")
        return root

    def _build_first_person_body(self) -> None:
        """Add a small view-attached body cue so looking down no longer feels like a floating floor camera."""
        try:
            ground = _rgb(self.scene, "ground", (80, 80, 70))
            boot_color = _shade(ground, -48)
            hand_color = _shade(_rgb(self.scene, "accent", (160, 210, 255)), -55)
            body_parts = [
                ("left_boot", self._make_box("left_boot", 0.24, 0.62, 0.16, boot_color), (-0.23, 1.10, -1.42), (5, 0, 0)),
                ("right_boot", self._make_box("right_boot", 0.24, 0.62, 0.16, boot_color), (0.23, 1.10, -1.42), (-5, 0, 0)),
                ("left_hand", self._make_box("left_hand", 0.16, 0.26, 0.12, hand_color), (-0.58, 0.94, -0.74), (0, 0, -8)),
                ("right_hand", self._make_box("right_hand", 0.16, 0.26, 0.12, hand_color), (0.58, 0.94, -0.74), (0, 0, 8)),
            ]
            for _name, part, pos, hpr in body_parts:
                part.reparentTo(self.cam_node)
                part.setPos(*pos)
                part.setHpr(*hpr)
                part.setLightOff(1)
                part.setDepthWrite(False)
                part.setDepthTest(False)
                part.setBin("fixed", 45)
            _scenario_log("INFO", "First-person standing body cues enabled: eye height 1.80m, boots/hands attached to camera view.")
        except Exception as exc:
            _scenario_log("WARN", f"First-person body cue setup failed; continuing without it: {exc}")

    def _setup_ambient_audio(self) -> None:
        terrain = str(self.scene.get("terrain", "rocky"))
        try:
            audio_path = self.audio_dir / f"ambient_{terrain}.wav"
            created = _write_ambient_wav(audio_path, terrain, str(self.scenario.get("object_name", "scenario")))
            sound = self.loader.loadSfx(str(audio_path))
            if sound is None:
                _scenario_log("WARN", f"Ambient audio could not be loaded: {audio_path}")
                return
            profile = _ambient_audio_profile(terrain)
            sound.setLoop(True)
            sound.setVolume(float(profile.get("volume", 0.30)))
            sound.play()
            self.ambient_sound = sound
            _scenario_log("INFO", f"Ambient audio {'generated' if created else 'reused'} and started: {audio_path}; terrain={terrain}; loop=True; volume={float(profile.get('volume', 0.30)):.2f}")
        except Exception as exc:
            _scenario_log("WARN", f"Ambient audio setup failed; scenario continues silently: {exc}")

    def _build_hud(self) -> None:
        OnscreenText = self._panda["OnscreenText"]
        self.hud = OnscreenText(
            text="",
            pos=(-1.28, 0.92),
            scale=0.043,
            align=0,
            mayChange=True,
            fg=(0.92, 0.95, 1.0, 1.0),
            bg=(0.02, 0.025, 0.04, 0.55),
            shadow=(0, 0, 0, 0.8),
        )
        self.help = OnscreenText(
            text="WASD move | mouse look | Space jump | C track target | J journal | T telescope | P pause | +/- time speed | Pos1/Home screenshot | F11 window/fullscreen | Esc quit",
            pos=(0, -0.94),
            scale=0.038,
            align=0,
            mayChange=False,
            fg=(0.86, 0.9, 0.96, 0.95),
            bg=(0.02, 0.02, 0.03, 0.55),
        )
        self.journal = OnscreenText(
            text=(
                "Journal / field pack\n"
                "- Telescope: T toggles narrow field-of-view.\n"
                "- Field binoculars: mouse wheel adjusts zoom.\n"
                "- Target tracker: C locks the CAD target in screen center.\n"
                "- Field manual: WASD move, Space jump, Home screenshot, Esc quit.\n"
                "- Notes: Educational approximation only; not an observing forecast."
            ),
            pos=(-1.24, 0.48),
            scale=0.040,
            align=0,
            mayChange=False,
            fg=(0.92, 0.95, 1.0, 1.0),
            bg=(0.02, 0.025, 0.04, 0.72),
            shadow=(0, 0, 0, 0.8),
        )
        self.journal.hide()

    def _install_controls(self) -> None:
        self.base.accept("escape", self._quit)
        self.base.accept("space", self._jump)
        self.base.accept("p", self._toggle_pause)
        self.base.accept("c", self._toggle_target_tracking)
        self.base.accept("j", self._toggle_journal)
        self.base.accept("t", self._toggle_telescope)
        self.base.accept("f11", self._toggle_fullscreen)
        self.base.accept("home", self._save_screenshot)
        self.base.accept("f12", self._save_screenshot)
        self.base.accept("wheel_up", self._zoom_in)
        self.base.accept("wheel_down", self._zoom_out)
        self.base.accept("+", self._speed_up)
        self.base.accept("=", self._speed_up)
        self.base.accept("-", self._speed_down)
        self.task_mgr.add(self._update_task, "jpl-cad-panda3d-update")

    def _warm_renderer(self) -> None:
        try:
            self.base.graphicsEngine.renderFrame()
            self.base.graphicsEngine.renderFrame()
            _scenario_log("INFO", f"Renderer warm-up completed; shader_prebound={'yes' if self.shader is not None else 'no'}. Driver-level binary shader caches are managed by the GPU driver/Panda3D.")
        except Exception as exc:
            _scenario_log("WARN", f"Renderer warm-up failed; continuing: {exc}")

    def _terrain_at(self, x: float, y: float) -> float:
        return _terrain_height(x, y, str(self.scene.get("terrain", "rocky")))

    def _collides_at(self, x: float, y: float) -> bool:
        for cx, cy, radius, _name in self.colliders:
            if math.hypot(x - cx, y - cy) < (radius + self.player_radius):
                return True
        return False

    def _resolve_player_move(self, old_x: float, old_y: float, new_x: float, new_y: float) -> tuple[float, float]:
        if not self._collides_at(new_x, new_y):
            return new_x, new_y
        if not self._collides_at(new_x, old_y):
            return new_x, old_y
        if not self._collides_at(old_x, new_y):
            return old_x, new_y
        return old_x, old_y

    def _current_sample(self) -> dict[str, Any]:
        if not self.samples:
            return {}
        span = max(1, len(self.samples) - 1)
        idx = int((self.elapsed * self.time_speed * 0.35) % span)
        return dict(self.samples[idx])

    def _target_position(self, sample: dict[str, Any]) -> tuple[float, float, float]:
        az = math.radians(_safe_float(sample.get("az_deg"), 0.0))
        elev = math.radians(_safe_float(sample.get("elev_deg"), 10.0))
        distance = 72.0 if self.scenario.get("mode") != "neo" else 88.0
        x = math.sin(az) * math.cos(elev) * distance
        y = math.cos(az) * math.cos(elev) * distance
        z = 8.0 + math.sin(elev) * distance
        return x, y, z

    def _update_target(self) -> None:
        sample = self._current_sample()
        x, y, z = self._target_position(sample)
        self.target_np.setPos(x, y, z)
        scale = 1.0
        if self.telescope:
            scale *= 1.8
        if self.scenario.get("mode") == "neo":
            scale *= 1.3
        self.target_np.setScale(scale)
        self.target_np.setColor(1.0, 1.0, 1.0, 1.0)

    def _center_mouse_delta(self) -> tuple[int, int]:
        win = self.base.win
        if win is None or not win.hasPointer(0):
            return 0, 0
        pointer = win.getPointer(0)
        cx = win.getXSize() // 2
        cy = win.getYSize() // 2
        dx = pointer.getX() - cx
        dy = pointer.getY() - cy
        if abs(dx) > win.getXSize() // 2 or abs(dy) > win.getYSize() // 2:
            dx = dy = 0
        win.movePointer(0, cx, cy)
        return int(dx), int(dy)

    def _update_camera(self, dt: float) -> None:
        foot_z = self._terrain_at(self.player_x, self.player_y)
        z = foot_z + self.eye_height + self.jump_offset
        self.camera.setPos(self.player_x, self.player_y, z)
        if self.sky_np is not None:
            self.sky_np.setPos(self.player_x, self.player_y, z)
        if self.track_target and getattr(self, "target_np", None) is not None:
            self.camera.lookAt(self.target_np)
            try:
                self.yaw = float(self.camera.getH())
                self.pitch = float(self.camera.getP())
            except Exception:
                pass
        else:
            self.camera.setHpr(self.yaw, self.pitch, 0)

    def _update_task(self, task):
        KeyboardButton = self._panda["KeyboardButton"]
        dt = max(0.0, min(0.08, float(getattr(self.base.taskMgr.globalClock, "getDt")())))
        if not self.paused:
            self.elapsed += dt
        dx, dy = self._center_mouse_delta()
        sensitivity = 0.09 if not self.telescope else 0.045
        if not self.track_target:
            self.yaw -= dx * sensitivity
            self.pitch = _clamp(self.pitch - dy * sensitivity, -82.0, 82.0)

        if not self.grounded or self.jump_offset > 0.0 or abs(self.vertical_velocity) > 0.0:
            self.vertical_velocity -= 9.81 * dt
            self.jump_offset += self.vertical_velocity * dt
            if self.jump_offset <= 0.0:
                self.jump_offset = 0.0
                self.vertical_velocity = 0.0
                self.grounded = True

        watcher = self.base.mouseWatcherNode
        move = self.speed * (2.2 if (watcher.isButtonDown(KeyboardButton.shift()) or watcher.isButtonDown(KeyboardButton.asciiKey("q"))) else 1.0) * dt
        rad = math.radians(self.yaw)
        forward_x = -math.sin(rad)
        forward_y = math.cos(rad)
        right_x = math.cos(rad)
        right_y = math.sin(rad)
        mx = my = 0.0
        if watcher.isButtonDown(KeyboardButton.asciiKey("w")):
            mx += forward_x; my += forward_y
        if watcher.isButtonDown(KeyboardButton.asciiKey("s")):
            mx -= forward_x; my -= forward_y
        if watcher.isButtonDown(KeyboardButton.asciiKey("d")):
            mx += right_x; my += right_y
        if watcher.isButtonDown(KeyboardButton.asciiKey("a")):
            mx -= right_x; my -= right_y
        length = math.hypot(mx, my)
        if length > 0:
            old_x, old_y = self.player_x, self.player_y
            new_x = _clamp(self.player_x + (mx / length) * move, -95.0, 95.0)
            new_y = _clamp(self.player_y + (my / length) * move, -95.0, 95.0)
            self.player_x, self.player_y = self._resolve_player_move(old_x, old_y, new_x, new_y)
        self._update_target()
        self._update_camera(dt)
        self._update_hud()
        return task.cont

    def _update_hud(self) -> None:
        sample = self._current_sample()
        dist = _safe_float(sample.get("distance_km"), 0.0)
        elev = _safe_float(sample.get("elev_deg"), 0.0)
        az = _safe_float(sample.get("az_deg"), 0.0)
        self.hud.setText(
            f"Panda3D Play Scenario | {self.scenario.get('object_name', 'object')}\n"
            f"{self.scenario.get('mode_label', '')} | body: {self.scenario.get('body_name', '')}\n"
            f"az {az:.1f}°  elev {elev:.1f}°  distance {dist:,.0f} km\n"
            f"time speed {self.time_speed:.2f}x | telescope {'ON' if self.telescope else 'off'} | target track {'ON' if self.track_target else 'off'} | {'PAUSED' if self.paused else 'running'}"
        )

    def _toggle_pause(self) -> None:
        self.paused = not self.paused
        _scenario_log("INFO", f"Pause toggled: {self.paused}")

    def _jump(self) -> None:
        if self.grounded:
            self.grounded = False
            self.vertical_velocity = 5.25
            self.jump_offset = max(0.02, self.jump_offset)
            _scenario_log("INFO", "Jump triggered via Space.")

    def _toggle_target_tracking(self) -> None:
        self.track_target = not self.track_target
        _scenario_log("INFO", f"Target tracking toggled: {self.track_target}")

    def _toggle_journal(self) -> None:
        self.journal_visible = not self.journal_visible
        try:
            if self.journal_visible:
                self.journal.show()
            else:
                self.journal.hide()
        except Exception:
            pass
        _scenario_log("INFO", f"Journal toggled: {self.journal_visible}")

    def _toggle_telescope(self) -> None:
        self.telescope = not self.telescope
        self._camera_lens().setFov(23 if self.telescope else 70)
        _scenario_log("INFO", f"Telescope toggled: {self.telescope}")

    def _speed_up(self) -> None:
        self.time_speed = min(16.0, self.time_speed * 1.35)

    def _speed_down(self) -> None:
        self.time_speed = max(0.10, self.time_speed / 1.35)

    def _zoom_in(self) -> None:
        lens = self._camera_lens()
        lens.setFov(max(10, lens.getFov()[0] * 0.85))

    def _zoom_out(self) -> None:
        lens = self._camera_lens()
        lens.setFov(min(85, lens.getFov()[0] / 0.85))

    def _save_screenshot(self) -> None:
        try:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)
            safe_obj = _sanitize_name(str(self.scenario.get("object_name", "scenario")))
            path = self.screenshot_dir / f"play_scenario_{safe_obj}_{time.strftime('%Y%m%d_%H%M%S')}.png"
            Filename = self._panda["Filename"]
            ok = False
            try:
                ok = bool(self.base.win.saveScreenshot(Filename.fromOsSpecific(str(path))))
            except Exception:
                result = self.base.screenshot(str(path), defaultFilename=False)
                ok = bool(result)
            if ok and path.exists():
                _scenario_log("INFO", f"Screenshot saved: {path}")
            else:
                _scenario_log("WARN", f"Screenshot request finished but file was not confirmed: {path}")
        except Exception as exc:
            _scenario_log("ERROR", f"Screenshot failed: {exc}")

    def _toggle_fullscreen(self) -> None:
        WindowProperties = self._panda["WindowProperties"]
        self.fullscreen = not self.fullscreen
        props = WindowProperties()
        props.setFullscreen(self.fullscreen)
        props.setCursorHidden(True)
        if not self.fullscreen:
            props.setSize(1280, 720)
        self.base.win.requestProperties(props)
        _scenario_log("INFO", f"Fullscreen toggled: {self.fullscreen}")

    def _quit(self) -> None:
        _scenario_log("INFO", "User requested scenario close.")
        self.base.userExit()

    def run(self) -> int:
        self.base.run()
        return 0


def run_panda3d_scenario(scenario_path: Path, render_device: str = "auto", shader_cache_dir: Path | None = None, shader_cache: str = "auto") -> int:
    _scenario_log("INFO", f"ENGINE_REQUEST=panda3d; render_device={render_device}; shader_cache={shader_cache}")
    try:
        _configure_panda(render_device, windowed=False)
        app = PandaScenarioApp(scenario_path, render_device=render_device, shader_cache_dir=shader_cache_dir or scenario_path.parent / "shader_cache", shader_cache=shader_cache)
        return app.run()
    except SystemExit:
        raise
    except Exception:
        _scenario_log("ERROR", "Panda3D scene failed with an unhandled exception.")
        _scenario_log("ERROR", traceback.format_exc())
        return 5


def open_html_fallback_notice(scenario_path: Path) -> int:
    _scenario_log("ERROR", "HTML/WebGL scenario mode is handled by the main GUI/browser view; no Panda3D subprocess renderer is available for this mode.")
    return 7


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a JPL CAD Play Scenario renderer.")
    parser.add_argument("scenario", help="Path to the generated scenario JSON file.")
    parser.add_argument("--engine", default=os.environ.get("JPL_CAD_SCENARIO_ENGINE", "auto"), choices=["auto", "panda3d", "panda", "html", "webgl"], help="Renderer engine selection.")
    parser.add_argument("--render-device", default=os.environ.get("JPL_CAD_SCENARIO_RENDER_DEVICE", "auto"), choices=["auto", "gpu", "opengl", "directx", "dx", "nvidia", "radeon", "amd", "intel", "cpu", "software", "tinydisplay"], help="Requested rendering backend/device preference. Exact GPU adapter selection is OS/driver dependent.")
    parser.add_argument("--shader-cache", default=os.environ.get("JPL_CAD_SCENARIO_SHADER_CACHE", "auto"), choices=["auto", "on", "off"], help="Prepare/reuse shader source cache files and bind them to the Panda3D low-poly geometry where possible.")
    parser.add_argument("--shader-cache-dir", default=os.environ.get("JPL_CAD_SCENARIO_SHADER_CACHE_DIR", ""), help="Directory for reusable shader source cache files.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = _parse_args(argv)
    scenario_path = Path(ns.scenario)
    engine = str(ns.engine or "auto").lower()
    render_device = str(ns.render_device or "auto").lower()
    shader_cache = str(ns.shader_cache or "auto").lower()
    shader_cache_dir = Path(ns.shader_cache_dir) if str(ns.shader_cache_dir or "").strip() else scenario_path.parent / "shader_cache"

    _scenario_log("INFO", f"Play Scenario subprocess started. engine={engine}; render_device={render_device}; shader_cache={shader_cache}; scenario={scenario_path}")
    if engine in {"html", "webgl"}:
        return open_html_fallback_notice(scenario_path)

    # Auto now means Panda3D first. Panda3D itself selects the best working backend configured below.
    result = run_panda3d_scenario(scenario_path, render_device=render_device, shader_cache_dir=shader_cache_dir, shader_cache=shader_cache)
    if result == 0:
        _scenario_log("INFO", "Panda3D renderer exited normally.")
    else:
        _scenario_log("ERROR", f"Panda3D renderer exited with code {result}. No legacy fallback renderer is present in this build; fix the Panda3D/backend issue shown above.")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
