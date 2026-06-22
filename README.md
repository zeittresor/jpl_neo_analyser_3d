# JPL CAD Ollama Explorer

A local-first Python/PyQt6 desktop application for querying NASA/JPL SBDB Close Approach Data (CAD), reviewing near-object close-approach records in a more readable form, generating optional local Ollama explanations, and opening local 3D close-approach visualizations.

Original source / updates: `github.com/zeittresor`

Version: `0.1.22`

## Purpose

JPL CAD Ollama Explorer is intended as an accessible desktop front end for the NASA/JPL CAD API. It helps users inspect close-approach records, convert key values into practical units, create local visualizations, and ask a locally running Ollama model for an explanatory assessment of the selected record.

The application is designed for educational, exploratory, and technical analysis workflows. It is not an official NASA/JPL tool and must not be used as an authoritative impact-risk predictor.

<img width="2560" height="1039" alt="jpl_cad_ollama_explorer_1" src="https://github.com/user-attachments/assets/5b1bc9ab-abe7-4c49-bfba-b4e9a53b33fc" />

<img width="2560" height="1037" alt="jpl_cad_ollama_explorer_2a" src="https://github.com/user-attachments/assets/503c943e-25a6-4787-a5a6-cc71b76d1eb0" />

<img width="2560" height="1039" alt="jpl_cad_ollama_explorer_2b" src="https://github.com/user-attachments/assets/dfbfdd1e-f06e-4f3a-8f7d-ecd66767d24d" />

<img width="2560" height="905" alt="jpl_cad_ollama_explorer_3" src="https://github.com/user-attachments/assets/d85d02a9-dcec-4ad7-8926-f814bcf28686" />

## Main features

- Query the NASA/JPL CAD API at `https://ssd-api.jpl.nasa.gov/cad.api`.
- Use GUI filters for date range, target body, maximum distance, object designation, sorting, object class, NEO/PHA/NEA/comet filters, relative velocity, and absolute magnitude, with localized hints for optional empty filter fields.
- Use built-in presets such as next-60-days Earth close approaches, nearby Earth approaches within 10 lunar distances, and Apophis 2029.
- Display CAD records in a readable table with converted values such as kilometers, lunar distances, min/max distance in km, 3-sigma distance span, miss distance in target-body radii, local impact-probability proxy, and approximate kinetic-energy context.
- Show the close-approach countdown directly in the table and in the selected-record detail panel.
- Show additional compact columns for local risk scoring, local impact-probability/proxy values when enough distance/radius data exist, approximate energy context, and rough satellite-relevance context.
- Load the last successful CAD result from a local cache on startup, automatically create an initial cache snapshot on first launch when no cache exists, and fall back to cache if a live CAD request fails later.
- Compare newly fetched CAD records with the previous cached fetch and show whether selected values are new, unchanged, or changed.
- Perform a lightweight public-NTP time/network check and pass that time/connectivity context to Ollama prompts.
- Show explicit selected-record detail fields with clear “not available” text when a CAD response does not provide a value.
- Show local non-official triage labels such as `Routine`, `Nearby`, `Close`, or `Very close`.
- Open a selected record in a local Plotly/WebGL HTML visualization with optional procedural textures for the target body and a visually enlarged flyby object.
- Run a simplified local what-if simulation comparing straight-line geometry, central-body gravity, and approximate Sun/major-planet tidal terms.
- Request a local Ollama analysis for the selected record on demand, including optional change-comparison context from the previous cached CAD fetch.
- Show a simple localized Ollama-unavailable dialog if the local Ollama service is not running, with options to start a found local Ollama executable, retry, or open the Ollama download page.
- Ask follow-up questions to Ollama using the selected CAD record and previous analysis as context.
- View Ollama responses in a formatted Markdown-like analysis pane with headings, emphasis, lists, and code blocks.
- Copy or print the formatted analysis output.
- Optionally read the latest answer or the full visible analysis aloud using Windows text-to-speech with Markdown formatting markers removed from spoken output.
- Use a localized Usage Notes tab for explanations of compact table values such as local impact-probability/proxy logic, derived scientific context fields, local risk scoring, satellite context, NTP time/network status, and LLM interpretation modes.
- Optionally suppress repeated educational/scientific limitation notes in Ollama responses and generated 3D HTML output.
- Choose whether Ollama should stay data-focused, provide a normal scientific assessment, or allow broader exploratory what-if estimates for follow-up questions.
- Choose whether local-computed/heuristic notes are explicitly shown or kept terse.
- Start maximized by default and use Ocean as the default theme on a fresh configuration.
- Switch between English, German, French, and Russian UI language files.
- Switch between bundled themes: Light, Dark, Sepia, Ocean, Matrix, Hellfire, and Purple.
- Choose flat colors, simple procedural textures, or enhanced procedural textures for generated 3D scenes.
- Use localized tooltips for the main controls and actions.
- Install into a project-local `.venv` while using a shared depot/cache path for reusable caches and optional managed tools.

## Scientific limitation

The JPL CAD API provides close-approach summary records. It does not provide the full state vector, full covariance, observational arc, full orbit solution, or official impact-probability analysis needed for authoritative orbit propagation.

The simulation module in this application is therefore an educational approximation. It starts from CAD-style miss distance and relative velocity data and constructs a simplified target-centered flyby. This can help illustrate scale, speed, timing, uncertainty ranges, and rough perturbation sensitivity, but it is not equivalent to JPL Horizons, SPICE, Sentry, or a professional orbit-determination pipeline.

For authoritative risk assessment, compare against official NASA/JPL/CNEOS resources, JPL Horizons/SPICE data, Minor Planet Center observations, and the newest published orbit updates.

## Requirements

- Windows 10/11 recommended
- Python 3.10 or 3.11 recommended
- Internet access for live CAD queries and first-time dependency installation
- Local Ollama installation only if local AI explanations are desired

Python dependencies are listed in `requirements.txt`.

## Windows quick start

Extract the ZIP or clone the repository, then run:

```bat
install_windows.bat
```

The installer creates a project-local `.venv`, asks for a shared depot/cache path, installs dependencies, and starts the application.

To run the application later:

```bat
run_windows.bat
```

## Shared PythonDepot / ToolDepot behavior

When a depot path such as `D:\PythonDepot` is selected, the installer uses it for reusable caches and optional shared tools:

```text
D:\PythonDepot\
  uv_cache\
  pip_cache\
  downloads\
  logs\
  tools\
    uv_venv\
  wheelhouse\
```

The installer tries to prepare a depot-managed `uv` installation in `tools\uv_venv\` and prefers that managed tool over a random globally installed `uv`. If `uv` is unavailable or fails, setup logs the issue and falls back to `.venv\Scripts\python.exe -m pip`.

Useful environment switches:

```bat
set JPL_CAD_NO_UV=1
```

Disables all `uv` usage and uses pip only.

```bat
set JPL_CAD_SKIP_MANAGED_UV=1
```

Skips preparation of depot-managed `uv`, but still allows an existing global `uv` if available.

## Offline / wheelhouse workflow

Build a wheelhouse while online:

```bat
build_wheelhouse_windows.bat
```

Then copy the project folder, including `wheelhouse\`, to the offline machine and run:

```bat
install_offline_windows.bat
```

The offline installer uses local wheelhouse files and the project-local virtual environment.

## Ollama usage

Default Ollama endpoint:

```text
http://localhost:11434
```

Start Ollama and ensure at least one model is installed. Inside the application, use **Refresh model list** to update the model selector, then choose a model and press the Ollama analysis button for the selected CAD record.

The application uses:

- `/api/tags` to list local models
- `/api/generate` for local analysis and follow-up responses

Ollama requests are made only when the user presses the corresponding button. CAD records are not sent to Ollama automatically.

The Ollama tab includes a 32k default context-length control with 4k-256k slider presets, a timeout setting, a running progress indicator, and an elapsed-time counter for long local model requests.

## CAD query notes

Common CAD parameters exposed in the GUI include:

- `date-min`, `date-max`: date range; values such as `now` and `+60` are supported by the API.
- `dist-max`: maximum distance; values may use au units such as `0.05` or lunar-distance values such as `10LD`.
- `body`: close-approach target body such as Earth, Moon, Mars, Jupiter, or all supported bodies.
- `des`: object designation, for example `99942` for Apophis.
- `sort`: sort order such as date, distance, relative speed, absolute magnitude, or object name.
- `diameter=true`: request diameter information when available.
- `fullname=true`: request formatted full object names.

When a specific object designation is used, the application sanitizes incompatible category filters before sending the API request. This prevents invalid CAD API combinations such as sending `neo=true` together with a specific `des` value.

## Themes and languages

Themes are loaded from `themes/*.json` and can be edited or extended without modifying application code. Included themes:

- Light
- Dark
- Sepia
- Ocean
- Matrix
- Hellfire
- Purple

Languages are loaded from `lang/*.json`. Included languages:

- English
- German
- French
- Russian

The installer uses English by default. The application UI language can be changed in Options.

## Output folders

Generated files are written under `output/` when needed. The last successful CAD API payload is cached under `cache/` so a later offline start can still show the last available dataset.

```text
cache/
  last_cad_payload.json
output/
  visualizations/
  logs/
```

Visualization files are local HTML files opened in the default browser. Error details and long diagnostic output may be written to `output/logs/`.

## Project layout

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
cache/
output/
```

## Documentation

- `docs/SCIENTIFIC_LIMITATIONS.md` explains the scientific boundaries of the local simulation.
- `docs/CHANGELOG.md` contains release notes.

## License

No license file is included in this package. Add a license before public redistribution if required.
