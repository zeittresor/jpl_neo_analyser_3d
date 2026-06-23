# Changelog

## v0.1.23

- Data table: Differently colored headers now mark app-derived columns such as countdown, risk score, local impact proxy, satellite note, energy estimate, and change status.
- Data table: App-derived cells receive subtle styling; values corrected by Ollama are highlighted separately.
- Options: Added a checkbox to allow or disable Ollama corrections for app-derived table fields.
- Ollama: Prompts now explicitly explain which visible fields are app-derived and may be checked/corrected, while CAD/API fields remain authoritative input data.
- Ollama: Added parsing for an optional structured APP_TABLE_CORRECTIONS block that can update app-derived display values for the selected row.
- Usage Notes: Added localized explanation of column coloring, value sources, and Ollama correction behavior.
- Documentation: Updated README to version 0.1.23 and kept it publication-oriented.

## v0.1.22

- 3D visualization: Added optional procedural texture modes (off, simple, enhanced) for generated HTML scenes.
- 3D visualization: Central bodies now use approximate body-specific textures such as Earth-like land/ocean, rocky cratered worlds, and banded gas giants.
- 3D visualization: Added a visually enlarged flyby object with a procedural small-body texture so the object itself is easier to see in the scene.
- Options: Added a new 3D object textures setting, saved in config and localized in the UI/tooltips.
- Documentation: Updated README to version 0.1.22 and kept it publication-oriented.

## v0.1.21

- Improved generated 3D HTML layout for ultrawide monitors by constraining the Plotly view to a readable centered viewport.
- Added theme-aware colors to generated 3D HTML output based on the selected app theme.
- Moved the large 3D scientific limitation banner out of the default HTML view; Usage Notes remain the primary place for explanatory limitations.
- The optional 3D scientific note is now off by default and, if enabled, appears as a compact collapsible note below the visualization instead of a full-width top banner.


## 0.1.20 - 2026-06-22

- Data table: Replaced missing-only impact handling with a local impact-probability/proxy calculation when distance, uncertainty interval and target-body radius data are available.
- Data table: Added derived scientific context columns for min/max distance in km, 3-sigma span in km, miss distance in target-body radii, and approximate kinetic energy in megatons TNT.
- Network/time: Added a public-NTP time/network check with system-clock fallback, displayed in the bottom status area.
- Analysis: Ollama prompts now include the current network/time context and the expanded derived scientific columns.
- Reliability: If a live CAD fetch fails while a previous cache exists, the app loads the cached CAD snapshot instead of leaving the user with only an error dialog.
- Usage Notes: Updated localized explanations for compact derived values, the local impact proxy, NTP status, and cache fallback behavior.
- Documentation: Updated README to version 0.1.20 and kept it publication-oriented.

## 0.1.19 - 2026-06-22

- UI: Added a localized Usage Notes tab for explanations that should not clutter the main data table.
- UI: Main-table missing CAD impact-probability values now use a compact dash instead of long explanatory text.
- Data table: Kept the Impact prob. % column concise while documenting its meaning in Usage Notes.
- Reliability: Fixed selected-record lookup after table sorting by matching visible object/date back to the underlying CAD record.
- Documentation: Updated README to version 0.1.19 and kept it publication-oriented.

## 0.1.18 - 2026-06-22

- UI: The main window now opens maximized by default and fresh configurations default to the Ocean theme.
- UI: Added scrollable simulation/options panes and adjusted the data table layout for better resizing.
- Data table: Added a live countdown/age column directly in the CAD table.
- Data table: Added local computed columns for risk score, CAD impact-probability availability, and rough satellite-relevance context.
- Analysis: Added an option to show or suppress local-computed/heuristic notes.
- Analysis: Added an LLM assessment-mode dropdown for data-focused, scientific assessment, or exploratory what-if behavior.
- Ollama: Follow-up prompts now receive the selected record plus visible computed columns and the chosen assessment mode.
- Documentation: Updated README to version 0.1.18 and kept it publication-oriented.

## 0.1.17 - 2026-06-22

- Ollama: Replaced raw connection-refused tracebacks with a simple localized dialog explaining that Ollama is not running or the configured URL is unreachable.
- Ollama: Added options in the dialog to start a locally found Ollama executable and retry, retry manually, or open the Ollama download page.
- Error handling: Ollama connection diagnostics are now written to `output/logs/ollama_connection_*.txt` instead of being shown directly to normal users.
- Documentation: Updated README to version 0.1.17 and kept it publication-oriented.

## 0.1.16 - 2026-06-22

- Data: Added localized placeholder hints to optional query filter fields such as designation, H min/max, and v_rel min/max so empty filters are no longer visually ambiguous.
- Data: Added a localized note under the query filters explaining that empty optional fields mean no restriction is applied for that value.
- UI: Added localized tooltips for the main CAD query filter inputs, not only the action buttons.
- Documentation: Updated README to version 0.1.16 and kept it publication-oriented.

## 0.1.15 - 2026-06-22

- Data: Added local CAD payload caching under `cache/last_cad_payload.json`; the app loads the last successful CAD result on startup and automatically creates an initial cache when no cache exists.
- Data: Added table columns showing whether each current CAD record is new, unchanged, changed, loaded from cache, or unavailable for comparison.
- Data: Added a selected-record details panel with explicit unavailable-value text for fields not provided by the CAD response.
- Data: Added a live countdown/elapsed-time display for the selected close-approach timestamp.
- Analysis: Ollama prompts now include local cache/change comparison context so changed CAD values can be discussed as newer measurement/orbit-solution refinements.
- Options: Added controls to show or suppress repeated scientific limitation/disclaimer notes in Ollama responses and 3D HTML output.
- 3D: Generated visualization HTML can now omit the educational limitation notice when the corresponding option is disabled.
- Documentation: Updated README to version 0.1.15 and kept it publication-oriented.

## 0.1.14 - 2026-06-21

- TTS: Read aloud now strips Markdown-style formatting markers before sending text to Windows text-to-speech.
- TTS: Headings, emphasis markers, bullet symbols, code fences, inline-code backticks, and Markdown links are converted to speech-friendly plain text.
- TTS: The visual formatted analysis pane is unchanged; only spoken text is cleaned.

## 0.1.13 - 2026-06-21

- Installer: Added a WinAPI console-color fallback for Python setup output when ANSI/Virtual Terminal colors are unavailable.
- Installer: Warning status prefixes now use orange (`[WARN]`) where supported, or the closest legacy Windows console warning color on classic cmd hosts.
- Installer: Kept output free of raw ANSI escape sequences while improving visual separation of warnings from normal information and command lines.

## 0.1.12 - 2026-06-21

- Ollama: Renamed the model button to Refresh model list and updated localized tooltips.
- Ollama: Changed the default context length from 8k to 32k and added an Ollama-style 4k/8k/16k/32k/64k/128k/256k slider while keeping numeric editing.
- TTS: Added an Options setting for Read aloud scope, defaulting to the latest assistant/local answer instead of reading the entire visible analysis/chat.
- TTS: Follow-up answers now update the latest readable response so Read aloud speaks the newest answer by default.
- Settings: Persist context length, temperature, timeout, and Read aloud scope in config.json.

## 0.1.11 - 2026-06-21

- Documentation: Replaced the outdated README with a publication-oriented current README for version 0.1.11.
- Documentation: Removed future-upgrade suggestions and version-note blocks from README; release history remains in `docs/CHANGELOG.md`.
- Documentation: README now reflects the current Ollama follow-up, formatted analysis, print, TTS, tooltip, depot-managed uv, language, and theme behavior.

## 0.1.10 - 2026-06-21

- Ollama: Simplified the language instruction to exactly `Answer strictly in <selected language>.` for both initial analysis and follow-up prompts.
- Ollama: Removed the previous extra German-specific exception text, because it could bias some local models toward German or make the instruction unnecessarily noisy.

## 0.1.9 - 2026-06-21

- Localization: Fixed the Options language combo initial state so a fresh English UI no longer shows DE as the selected language.
- Ollama: Initial analysis and follow-up prompts now explicitly request the selected UI language instead of defaulting to German.
- Local analysis: Local heuristic summaries now use language-specific text for EN/DE/FR/RU where available.
- TTS: Added optional Windows text-to-speech buttons for the formatted analysis output: Read aloud and Stop speech.
- TTS: Speech tries to select a voice culture matching the selected UI language and falls back to the system default voice if needed.

## 0.1.7 - 2026-06-21

- Ollama: Added an elapsed-time counter next to the indeterminate progress bar, so long local model requests visibly continue running.
- Ollama: The running-state label now shows elapsed seconds and the configured timeout while the user may switch tabs.
- UI: Kept local heuristic summary independent from an in-flight Ollama request; the ignore action remains available for late Ollama results.

## 0.1.6 - 2026-06-21

- Ollama: Switched generation requests to streaming mode internally, while still displaying the final collected response in the GUI. This avoids long non-streaming HTTP waits looking like a frozen request.
- Ollama: Added a configurable timeout field on the Ollama Analysis tab, defaulting to 600 seconds.
- UI: Added an indeterminate progress bar and status label while Ollama analysis is running. The user can switch tabs while the request continues.
- UI: Added an "Ignore running Ollama result" action so a later Ollama response cannot overwrite a local heuristic summary.
- Error handling: Replaced truncated QMessageBox tracebacks with a scrollable/copyable error-details dialog and automatic logs under `output/logs/`.

## 0.1.5 - 2026-06-21

- Installer: Disabled pip/uv Unicode progress bars during setup to avoid question-mark glyphs in older Windows consoles or fonts.
- Installer: Added `PIP_PROGRESS_BAR=off`, `PIP_NO_COLOR=1`, `UV_NO_PROGRESS=1`, `UV_COLOR=never`, and UTF-8 child-process environment settings for setup subprocesses.
- Installer: `pip install/download/wheel` commands now explicitly pass `--progress-bar off` where applicable.
- Reliability: Kept human-readable project status lines, but dependency installer progress now favors plain text over decorative console output.

## 0.1.4 - 2026-06-21

- API: Fixed specific-object queries such as Apophis 2029 by omitting incompatible CAD filter parameters (`neo`, `pha`, `nea`, `comet`, `class`, `h-min`, `h-max`, `v-rel-min`, `v-rel-max`) whenever `des` is set. The GUI checkbox state remains user-visible, but the API request is sanitized.
- Presets: Apophis 2029 now clears incompatible object-category filters in the GUI for better clarity.
- Localization: Expanded runtime language switching to more labels, buttons, checkboxes, group boxes, table headers, suffixes, options fields, and About/Simulation default text.
- Reliability: Added a small regression test path for CAD parameter generation and recompiled all Python modules.

## 0.1.3 - 2026-06-21

- Installer: Added optional depot-managed `uv` under the selected PythonDepot path, for example `D:\PythonDepot\tools\uv_venv\`.
- Installer: Prefer depot-managed `uv` over a random global `uv`, while keeping global `uv` as a fallback.
- Installer: Added `JPL_CAD_SKIP_MANAGED_UV=1` to skip depot-managed `uv` preparation without disabling global `uv`.
- Wheelhouse: `build_wheelhouse_windows.bat` now downloads the `uv` package into `wheelhouse/` so offline installs can prepare managed `uv` from local files when possible.
- Reliability: `uv` remains optional; any `uv` failure logs details under `install_logs/` and falls back to venv `pip`.

## 0.1.2 - 2026-06-21

- Installer: Treat global `uv` as an optional accelerator only. If `uv pip install --python .venv\Scripts\python.exe ...` fails, setup now automatically retries with `.venv\Scripts\python.exe -m pip install ...` instead of aborting.
- Installer: `uv` failure output is written to `install_logs/uv_install_failed.log` so the console stays readable before pip fallback.
- Installer: Set `JPL_CAD_NO_UV=1` to skip the optional `uv` attempt completely.
- Installer: Added a venv Python sanity check and automatic recreation of a broken `.venv`.
- Installer: Kept ANSI/Virtual Terminal fallback from 0.1.1 so Windows consoles should not show raw escape sequences.

## 0.1.1 - 2026-06-21

- Fixed Windows installer color handling in `scripts/setup_env.py`.
- Python-side setup output now enables Virtual Terminal Processing on Windows when available.
- If ANSI cannot be enabled, output is plain text instead of raw escape codes.
- Bumped application version from 0.1.0 to 0.1.1.

## 0.1.0 - 2026-06-21

- Initial JPL CAD Ollama Explorer release.
