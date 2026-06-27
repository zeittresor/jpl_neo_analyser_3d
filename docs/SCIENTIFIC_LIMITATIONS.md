# Scientific limitations

This app intentionally separates four layers:

1. Official source data from NASA/JPL CAD.
2. Local readable interpretation and simple derived units.
3. Local screening context such as current-encounter score, impact proxy, energy context, and broad spacecraft/probe-region matching.
4. Local educational simulation and local LLM explanation.

Only layer 1 is official source data. Layers 2, 3, and 4 are convenience, interpretation, screening, or educational layers.

## Why CAD alone is not enough for real orbit prediction

A CAD record contains a close-approach summary: designation, orbit ID, close-approach time, nominal distance, min/max distance range, relative velocity, v-infinity, uncertainty text, target body, H magnitude, and optional diameter/full-name fields.

That is enough for readable close-approach summaries, but not enough for authoritative orbit propagation. Real propagation needs a state vector and often covariance data, observation arc metadata, dynamical model selection, non-gravitational parameters for comets or active bodies, relativistic corrections in high-precision contexts, and updated observations.

## What the app-derived risk/context fields do

The app-derived fields are intended to help triage and compare records in the visible table. They are not official classifications.

- `Risk score` is a current close-approach/encounter score derived from the selected CAD encounter, not a long-term PHA/MOID orbital-hazard score.
- `Impact prob. %` is a local proxy only when the available min/max distance interval overlaps the target-body radius. It should not be treated as an official probability.
- `Energy Mt TNT` is an approximate kinetic-energy context estimate based on approximate size and velocity assumptions where possible.
- `Spacecraft context` is a broad radial-region screening match against a local catalog of artificial-object environments. It is not a conjunction analysis.

## Spacecraft/probe context catalog

The local `data/spacecraft_regions.json` file contains approximate artificial-object regions, including Earth satellite shells, cislunar/lunar regions, selected Lagrange-point distance shells, and selected planetary orbiter regions.

This catalog does not contain live TLEs, SPICE kernels, Horizons vectors, spacecraft ephemerides, station-keeping windows, attitude/operational states, or real conjunction predictions. A catalog match means only that the CAD distance interval overlaps a broad region where artificial objects may exist.

## What the built-in simulation does

The built-in simulation creates a synthetic target-centered flyby:

- x axis: direction of relative velocity
- y axis: CAD miss distance
- z axis: zero at initial geometry
- time zero: close approach

It compares:

- straight-line geometry
- central-body gravity only
- central-body gravity plus approximate solar and planetary tidal terms

This is useful for intuition: scale, speed, gravitational focusing, and rough perturbation sensitivity.

## What the surface/flyby viewpoint and Play Scenario modes do

The surface/flyby viewpoint view uses the same synthetic trajectory to create a local HTML sky-view approximation. In target-surface mode, the observer is placed at an idealized sub-approach surface point. In flyby-object mode, the observer is placed on the synthetic flyby object and looks back at the target body.

The optional Panda3D **Play this scenario** mode uses the same simplified sky direction samples to create a fullscreen, game-like educational scene. It adds stylized terrain, generated 3D objects, procedural textures, target markers, first-person camera/body cues, procedural ambient audio and telescope/zoom controls. These are deliberately immersive aids, not measured landscapes, real local soundscapes, visibility calculations or mission-grade renderings.

These views do not compute real geographic coordinates, target-body rotation, local horizon masking by terrain, daylight, atmosphere, apparent magnitude, camera attitude, phase angle, SPICE kernels, Horizons vectors, or mission-grade observer geometry. They are visual geometry/education aids only.

## What it must not be used for

Do not use this app to claim:

- official impact probability
- precise future coordinates
- official risk classification
- exact deflection due to planets
- exact conjunctions with spacecraft, probes, satellites, stations, or Lagrange-point missions
- impact/no-impact certainty

Use official CNEOS/JPL/MPC/Horizons/SPICE resources for that.


## Panda3D education scenery

The optional fullscreen scenario mode uses original, procedurally generated stylized low-poly/cartoon-like scenery. It is meant to make the selected CAD-derived geometry more intuitive and engaging. The landscapes, lighting and texture cues are artistic educational approximations, not real terrain, real local weather, true observing conditions, real spacecraft camera views or an ephemeris-grade visualization.
