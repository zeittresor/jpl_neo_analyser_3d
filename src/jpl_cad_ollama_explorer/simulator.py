# source: https://github.com/zeittresor
from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, sin

import numpy as np

from .cad_models import CadRecord
from .constants import AU_KM, CIRCULAR_ORBITS, DAY_SECONDS, J2000_JD, MU


@dataclass(slots=True)
class SimulationSettings:
    days_before: float = 7.0
    days_after: float = 7.0
    step_minutes: float = 60.0
    include_sun: bool = True
    include_major_planets: bool = True
    exaggeration: float = 1.0


@dataclass(slots=True)
class SimulationResult:
    times_days: np.ndarray
    straight: np.ndarray
    two_body: np.ndarray
    n_body: np.ndarray | None
    central_body: str
    metadata: dict[str, str]

    def min_distance_km(self, path: np.ndarray) -> float:
        if path.size == 0:
            return float("nan")
        return float(np.min(np.linalg.norm(path, axis=1)))


def circular_position(body_code: str, jd: float) -> np.ndarray:
    if body_code not in CIRCULAR_ORBITS:
        return np.zeros(3)
    a_au, period_days, phase_deg = CIRCULAR_ORBITS[body_code]
    angle = (phase_deg + 360.0 * ((jd - J2000_JD) / period_days)) * pi / 180.0
    return np.array([a_au * AU_KM * cos(angle), a_au * AU_KM * sin(angle), 0.0], dtype=float)


def _acceleration_target_frame(
    r: np.ndarray,
    t_seconds: float,
    jd_ca: float,
    central_body: str,
    include_sun: bool,
    include_major_planets: bool,
) -> np.ndarray:
    distance = np.linalg.norm(r)
    if distance <= 1e-9:
        distance = 1e-9
    mu_c = MU.get(central_body, MU["Earth"])
    acc = -mu_c * r / (distance**3)

    jd = jd_ca + t_seconds / DAY_SECONDS
    target_helio = circular_position(central_body, jd)

    if include_sun and central_body != "Sun":
        # Tidal acceleration of the Sun in a target-centered frame.
        sun_rel = -target_helio
        sun_d = np.linalg.norm(sun_rel)
        if sun_d > 1e-9:
            obj_to_sun = sun_rel - r
            obj_d = np.linalg.norm(obj_to_sun)
            acc += MU["Sun"] * (obj_to_sun / (obj_d**3) - sun_rel / (sun_d**3))

    if include_major_planets:
        for code in ("Merc", "Venus", "Earth", "Mars", "Juptr", "Satrn", "Urnus", "Neptn"):
            if code == central_body or code not in MU:
                continue
            planet_rel = circular_position(code, jd) - target_helio
            planet_d = np.linalg.norm(planet_rel)
            if planet_d <= 1e-9:
                continue
            obj_to_planet = planet_rel - r
            obj_d = np.linalg.norm(obj_to_planet)
            if obj_d <= 1e-9:
                continue
            acc += MU[code] * (obj_to_planet / (obj_d**3) - planet_rel / (planet_d**3))
    return acc


def _rk4_step(state: np.ndarray, dt: float, accel_func) -> np.ndarray:
    def deriv(s: np.ndarray) -> np.ndarray:
        return np.concatenate([s[3:6], accel_func(s[:3])])

    k1 = deriv(state)
    k2 = deriv(state + 0.5 * dt * k1)
    k3 = deriv(state + 0.5 * dt * k2)
    k4 = deriv(state + dt * k3)
    return state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)


def simulate_close_approach(record: CadRecord, settings: SimulationSettings) -> SimulationResult:
    """Build a simplified target-centered flyby simulation from CAD close-approach data.

    CAD data does not contain a full state vector or orbital covariance. This simulation therefore
    starts with a synthetic closest-approach geometry: the object passes the selected body at the CAD
    miss distance with CAD relative speed. The comparison is still useful for intuition: straight
    line vs. central-body gravity vs. approximate tidal perturbations.
    """
    central = record.body_code if record.body_code != "ALL" else "Earth"
    if central not in MU:
        central = "Earth"

    miss_km = record.distance_km or 10.0 * 384_400.0
    speed_kms = record.v_rel_kms or 12.0
    jd_ca = record.jd or J2000_JD

    dt_seconds = max(60.0, settings.step_minutes * 60.0)
    start_seconds = -settings.days_before * DAY_SECONDS
    end_seconds = settings.days_after * DAY_SECONDS
    times = np.arange(start_seconds, end_seconds + 0.5 * dt_seconds, dt_seconds, dtype=float)

    # Synthetic geometry: closest approach at t=0, x velocity, y miss distance.
    straight = np.column_stack([speed_kms * times, np.full_like(times, miss_km), np.zeros_like(times)])

    # Integrate from the first point forward using the same initial state.
    state0 = np.array([straight[0, 0], miss_km, 0.0, speed_kms, 0.0, 0.0], dtype=float)

    two_body = np.zeros((len(times), 3), dtype=float)
    n_body = np.zeros((len(times), 3), dtype=float)
    state_two = state0.copy()
    state_n = state0.copy()
    two_body[0] = state_two[:3]
    n_body[0] = state_n[:3]
    current_time = times[0]

    for idx in range(1, len(times)):
        dt = times[idx] - times[idx - 1]
        mid_time = current_time + 0.5 * dt

        def acc_two(r: np.ndarray) -> np.ndarray:
            return _acceleration_target_frame(r, mid_time, jd_ca, central, False, False)

        def acc_n(r: np.ndarray) -> np.ndarray:
            return _acceleration_target_frame(
                r,
                mid_time,
                jd_ca,
                central,
                settings.include_sun,
                settings.include_major_planets,
            )

        state_two = _rk4_step(state_two, dt, acc_two)
        state_n = _rk4_step(state_n, dt, acc_n)
        current_time = times[idx]
        two_body[idx] = state_two[:3]
        n_body[idx] = state_n[:3]

    metadata = {
        "warning": "Educational approximation from CAD miss distance and relative velocity, not orbit determination.",
        "central_body": central,
        "miss_distance_km": f"{miss_km:.3f}",
        "relative_speed_kms": f"{speed_kms:.6f}",
        "jd_ca": f"{jd_ca:.9f}",
    }
    return SimulationResult(
        times_days=times / DAY_SECONDS,
        straight=straight,
        two_body=two_body,
        n_body=n_body if (settings.include_sun or settings.include_major_planets) else None,
        central_body=central,
        metadata=metadata,
    )
