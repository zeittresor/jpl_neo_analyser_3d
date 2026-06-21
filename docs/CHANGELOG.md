# Changelog

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
