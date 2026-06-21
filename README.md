# JPL CAD Ollama Explorer

A local-first Python/PyQt6 desktop GUI for NASA/JPL SBDB Close Approach Data (CAD), local Ollama explanations, and a local 3D close-approach visualization.

Original source / updates: `github.com/zeittresor`

Version: `0.1.4`

## What it does

- Queries the NASA/JPL CAD API: `https://ssd-api.jpl.nasa.gov/cad.api`
- Presents asteroid/comet close approaches in a more readable table.
- Converts distances into km and lunar distances.
- Adds a local non-official triage label such as `Routine`, `Nearby`, `Close`, or `Very close`.
- Sends the selected record to a local Ollama instance only when you press the analysis button.
- Creates a self-contained local Plotly/WebGL HTML visualization that can be opened in the browser.
- Runs a simplified gravitational what-if comparison:
  - straight-line CAD geometry
  - central-body gravity only
  - approximate Sun and major-planet tidal perturbations

## Important scientific limitation

The JPL CAD API provides close-approach summary records. It does not provide the full state vector, full covariance, observational arc, or complete orbit solution needed for authoritative orbit propagation or impact-risk analysis.

The simulation in this app is therefore an educational approximation. It starts from the CAD miss distance and relative velocity and creates a synthetic target-centered flyby. Use it to understand scale, velocity, uncertainty brackets, and possible perturbation sensitivity. Do not use it as an impact-risk prediction tool.

For authoritative analysis, verify with official JPL/CNEOS pages, JPL Horizons/SPICE kernels, Minor Planet Center data, and current observation updates.

## Requirements

- Windows 10/11 or a compatible desktop OS
- Python 3.10 or 3.11 recommended
- Internet access for live JPL CAD queries and first-time package installation
- Local Ollama only if you want AI explanations

Python packages:

```text
PyQt6
requests
numpy
plotly
```

## Windows quick start

1. Extract the ZIP.
2. Run:

```bat
install_windows.bat
```

The installer creates a project-local `.venv`, uses a shared depot/cache location if possible, installs dependencies, and then starts the app.

To run later:

```bat
run_windows.bat
```


## Shared PythonDepot and uv

When you select a depot/cache path such as `D:\PythonDepot`, the installer now uses it for more than package caches:

```text
D:\PythonDepot\
  uv_cache\
  pip_cache\
  downloads\
  logs\
  tools\uv_venv\
  wheelhouse\
```

The installer prepares a depot-managed `uv` installation in `tools\uv_venv\` when possible and uses `UV_CACHE_DIR` / `PIP_CACHE_DIR` inside the selected depot. This makes `uv` reusable for this project without relying on a random global `uv` from another Python installation.

`uv` is still optional. If it fails, setup writes a log under `install_logs/` and falls back to `.venv\Scripts\python.exe -m pip`.

Useful environment switches:

```bat
set JPL_CAD_NO_UV=1
```

Skip all `uv` use and use pip only.

```bat
set JPL_CAD_SKIP_MANAGED_UV=1
```

Skip preparing depot-managed `uv`, but still allow an existing global `uv` if available.

## Offline / wheelhouse workflow

Build wheelhouse while online:

```bat
build_wheelhouse_windows.bat
```

Then copy the project including `wheelhouse/` to an offline machine and run:

```bat
install_offline_windows.bat
```

## Ollama setup

Default endpoint:

```text
http://localhost:11434
```

Start Ollama and make sure a model is available, for example:

```bat
ollama pull gemma4:26b
ollama serve
```

Inside the app, use **List models** to fill the model selector. The app uses Ollama's `/api/tags` endpoint to list local models and `/api/generate` with `stream=false` for one-shot analysis.

## CAD query notes

Useful CAD parameters exposed in the GUI:

- `date-min`, `date-max`: date range. `now` and `+60` are supported by the API.
- `dist-max`: distance maximum. You can use au values like `0.05` or lunar-distance values like `10LD`.
- `body`: Earth, Moon, Mars, Jupiter, etc., or all bodies.
- `des`: object designation, e.g. `99942` for Apophis.
- `sort`: sort by date, distance, relative speed, H, object, etc.
- `diameter=true`: include known diameter values if available.
- `fullname=true`: include formatted full names.

## Presets

- Next 60 days: default Earth NEO close approaches under 0.05 au.
- `< 10 LD / 365 days`: nearby Earth approaches in the next year sorted by distance.
- Apophis 2029: example query for 99942 Apophis in 2029.

## Themes and languages

Themes are loaded from `themes/*.json`. The included themes are:

- Light
- Dark
- Sepia
- Ocean
- Matrix
- Hölle / Hellfire
- Purple

Languages are loaded from `lang/*.json`. Included language files are English, German, French, and Russian. English remains the installer/default language.

## Files and folders

```text
app.py
requirements.txt
install_windows.bat
run_windows.bat
build_wheelhouse_windows.bat
install_offline_windows.bat
src/jpl_cad_ollama_explorer/
lang/
themes/
docs/
output/visualizations/
```

## Suggested future upgrades

- Optional Horizons/SPICE mode for real state-vector propagation.
- MPC observation import.
- SBDB object-detail lookup per selected designation.
- Cached CAD query history.
- Export CSV/Markdown reports.
- More advanced covariance visualization when suitable source data is available.


## Version 0.1.1

Maintenance fix: the Python setup script now enables Windows Virtual Terminal ANSI support only when possible and otherwise falls back to plain text output. This prevents raw sequences such as `\x1b[96m` from appearing during installation on hosts where ANSI processing is disabled.


## Version 0.1.3

Maintenance fix: the installer now prepares an optional depot-managed `uv` installation under the selected PythonDepot path, e.g. `D:\PythonDepot\tools\uv_venv\`. Wheelhouse builds also download the `uv` package so offline machines can prepare managed `uv` from `wheelhouse/` when available. `uv` remains optional and setup always falls back to venv pip if it fails.


## Notes for v0.1.4

- Specific-object CAD searches, for example Apophis via designation `99942`, now omit incompatible category filters before calling the JPL API. This avoids API error 400 messages such as `filter neo not allowed when specifying a specific object with spk or des`.
- Runtime language switching now updates substantially more static GUI text: group boxes, labels, buttons, checkboxes, table headers, unit suffixes, body names, and the About/Simulation default text.
