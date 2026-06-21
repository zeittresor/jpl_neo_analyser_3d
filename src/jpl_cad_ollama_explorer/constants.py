# source: https://github.com/zeittresor
"""Constants for the JPL CAD Ollama Explorer.

The simulation constants are intentionally compact and dependency-light.
They are sufficient for approximate educational what-if comparisons, not
for mission-grade ephemerides or impact-risk decisions.
"""
from __future__ import annotations

AU_KM = 149_597_870.700
LD_KM = 384_400.0
DAY_SECONDS = 86_400.0
J2000_JD = 2_451_545.0

# Gravitational parameters, km^3/s^2. Values rounded enough for educational use.
MU = {
    "Sun": 132_712_440_018.0,
    "Merc": 22_032.0,
    "Venus": 324_859.0,
    "Earth": 398_600.435436,
    "Moon": 4_902.800066,
    "Mars": 42_828.375214,
    "Juptr": 126_712_764.8,
    "Satrn": 37_940_585.2,
    "Urnus": 5_794_556.4,
    "Neptn": 6_836_527.1,
    "Pluto": 871.0,
}

BODY_DISPLAY = {
    "Merc": "Mercury",
    "Venus": "Venus",
    "Earth": "Earth",
    "Mars": "Mars",
    "Juptr": "Jupiter",
    "Satrn": "Saturn",
    "Urnus": "Uranus",
    "Neptn": "Neptune",
    "Pluto": "Pluto",
    "Moon": "Moon",
    "ALL": "All bodies",
}

BODY_CODES = ["Earth", "Moon", "Merc", "Venus", "Mars", "Juptr", "Satrn", "Urnus", "Neptn", "Pluto", "ALL"]

BODY_RADIUS_KM = {
    "Sun": 696_340.0,
    "Merc": 2_439.7,
    "Venus": 6_051.8,
    "Earth": 6_378.137,
    "Moon": 1_737.4,
    "Mars": 3_389.5,
    "Juptr": 69_911.0,
    "Satrn": 58_232.0,
    "Urnus": 25_362.0,
    "Neptn": 24_622.0,
    "Pluto": 1_188.3,
}

# Very rough circular-orbit elements for perturbation visualization.
# Semimajor axis in AU, orbital period in days, mean longitude-ish phase at J2000 in degrees.
CIRCULAR_ORBITS = {
    "Merc": (0.387098, 87.969, 252.25),
    "Venus": (0.723332, 224.701, 181.98),
    "Earth": (1.000000, 365.256, 100.46),
    "Mars": (1.523679, 686.980, 355.43),
    "Juptr": (5.2044, 4332.589, 34.35),
    "Satrn": (9.5826, 10759.22, 50.08),
    "Urnus": (19.2184, 30685.4, 314.05),
    "Neptn": (30.1104, 60189.0, 304.35),
    "Pluto": (39.482, 90560.0, 238.93),
}

ORBIT_CLASS_DESCRIPTIONS = {
    "IEO": "Atira / interior-Earth object",
    "ATE": "Aten near-Earth asteroid",
    "APO": "Apollo near-Earth asteroid",
    "AMO": "Amor near-Earth asteroid",
    "MCA": "Mars-crossing asteroid",
    "IMB": "Inner main-belt asteroid",
    "MBA": "Main-belt asteroid",
    "OMB": "Outer main-belt asteroid",
    "TJN": "Jupiter Trojan",
    "CEN": "Centaur",
    "TNO": "Trans-Neptunian object",
    "PAA": "Parabolic asteroid",
    "HYA": "Hyperbolic asteroid",
    "HYP": "Hyperbolic comet",
    "PAR": "Parabolic comet",
    "COM": "Comet",
    "JFC": "Jupiter-family comet",
    "HTC": "Halley-type comet",
    "ETc": "Encke-type comet",
    "CTc": "Chiron-type comet",
    "JFc": "Jupiter-family comet",
}
