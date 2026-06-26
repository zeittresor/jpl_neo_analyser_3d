# Changelog

## 0.1.44 - 2026-06-26

- Play Scenario: Fixed the Pygame software renderer leaving stale backbuffer pixels below the sky area when the camera moved.
- Play Scenario: Reduced the fixed foreground shadow overlay so it no longer looks like a non-perspective 2D panel.
- Documentation: Updated README to version 0.1.44.

## 0.1.43 - 2026-06-26

- Play Scenario rendering: Reset OpenGL texture/blend/depth/cull state at frame boundaries so text/ground textures no longer bleed into the sky/background after mouse movement.
- Play Scenario camera: Replaced rotation-order camera setup with an explicit look-matrix matching the WASD/target coordinate convention, so mouse pitch/yaw behave like a normal first-person view.
- Play Scenario terrain: Rewound terrain quads to render as top-facing ground, enabled terrain-only back-face culling, and expanded the terrain draw radius to reduce underside/edge artifacts when looking steeply up or down.
- Play Scenario sky: Made the horizon haze follow camera pitch instead of remaining fixed like a 2D wallpaper.
- Documentation: Updated README to version 0.1.43.

## 0.1.42 - 2026-06-25

- Play Scenario robustness: Wrapped the Pyglet/OpenGL renderer so unhandled startup/render exceptions are printed to the Play Scenario log and then trigger the legacy software-rendered fallback instead of silently closing.
- Play Scenario fallback: Added `pygame>=2.5,<3` to the standard requirements as a fallback renderer dependency while keeping Pyglet/OpenGL as the primary engine.
- Log tab: Copy to Clipboard now copies the complete in-memory app session log, not only the currently visible text area, so it still works after Clear View.
- Documentation: Updated README to version 0.1.42.

## 0.1.41 - 2026-06-25

- Play Scenario diagnostics: Launch the Pyglet/OpenGL scenario subprocess without a transient console window and capture stdout/stderr into `output/logs/play_scenario_*.txt`.
- Play Scenario diagnostics: Poll the scenario subprocess and show non-zero exits in the new Log tab with the last log lines, so fullscreen startup failures are no longer lost.
- Logging UI: Added a dedicated Log tab with Copy to Clipboard, Open Log Folder and Clear View buttons.
- App diagnostics: Added session log files (`output/logs/app_session_*.txt`), central `_write_error_log` mirroring into the Log tab, and an uncaught-exception hook for GUI/runtime errors.
- Documentation: Updated README to version 0.1.41.

## 0.1.40 - 2026-06-25

- Installer/uv fallback: Fixed a venv-loss regression introduced by the uv-created-venv repair path. If `uv venv` fails after removing `.venv`, the installer now immediately restores a normal `python -m venv` before falling back to pip.
- Installer robustness: Added missing-interpreter checks before venv sanity probes and before final pip fallback, preventing raw `FileNotFoundError: [WinError 2]` tracebacks when `.venv\Scripts\python.exe` is absent.
- Installer diagnostics: Missing executable cases now write `command_executable_not_found.log` / `venv_python_missing.log` instead of crashing without a targeted installer log.
- Documentation: Updated README to version 0.1.40.

## 0.1.39 - 2026-06-25

- Play Scenario: Changed the primary fullscreen education mode from the legacy Pygame software renderer to a Pyglet/OpenGL first-person 3D scene.
- Play Scenario: Added a real OpenGL camera with X/Y/Z world movement, mouse yaw/pitch looking, fullscreen controls, procedural terrain textures and generated low-poly world objects.
- Play Scenario: Kept the old Pygame renderer only as a best-effort fallback if pyglet or OpenGL cannot initialize.
- Installer/dependencies: Replaced the primary scenario dependency with `pyglet>=2.1,<3`; `pygame` remains only in optional requirements for the legacy fallback renderer.
- Documentation: Updated README, usage notes and scientific limitations for the Pyglet/OpenGL scenario engine.

## 0.1.38 - 2026-06-25

- Pygame education mode: Replaced the earlier parallax-like scene impression with a lightweight software-projected X/Y/Z renderer. WASD now changes camera position through a generated world, and mouse look supports both yaw and pitch.
- Pygame education mode: Added perspective-projected terrain tiles, low-poly tree/rock meshes, terrain height, depth sorting, open walking path logic and stronger 3D visual cues without external assets or OpenGL dependencies.
- Installer/uv: Added a second repair strategy for uv-specific venv inspection failures. If `python -m venv` repair still cannot be inspected by uv, the installer now tries to recreate the project venv with `uv venv --python <base-python>` before falling back to pip.
- Diagnostics: Added logs for the uv-created venv path (`uv_created_venv_attempt.log`, `uv_created_venv_failed.log`, `uv_created_venv_pip_bootstrap_failed.log`, and `uv_venv_probe_failed_after_python_repair.log`).
- Documentation: Updated README to version 0.1.38.

## 0.1.37 - 2026-06-25

- Installer robustness: Added a uv recovery path for malformed or stale project-local virtual environments. If uv cannot inspect `.venv\Scripts\python.exe`, the installer now recreates the `.venv`, bootstraps pip/setuptools/wheel, re-validates uv, and retries before falling back to pip.
- Installer robustness: Added a second uv dependency-install attempt after a best-effort `uv cache clean` when the first uv install attempt fails.
- Logging: uv probe and repair attempts now write explicit logs (`uv_venv_repair_attempt.log`, `uv_venv_probe_failed_after_repair.log`, `uv_install_failed_first.log`, `uv_install_failed_second.log`) while preserving `uv_install_failed.log` as the latest uv failure pointer.
- Documentation: Updated README to version 0.1.37 and documented the uv repair/retry behavior.

## 0.1.36 - 2026-06-24

- Startup fix: Restored the exported package metadata field `__app_name__`, fixing an ImportError that prevented the GUI from starting after the v0.1.35 installer completed.
- Installer: Added a post-install smoke check for package metadata so this class of regression is caught before launching the app.
- Installer/uv: Added an explicit uv compatibility probe for the project-local venv. If uv cannot inspect the venv Python on a specific Windows/Python setup, the installer now skips uv cleanly and falls back to venv pip without attempting the failing uv install step.
- Installer/diagnostics: uv probe failures are written to `install_logs/uv_venv_probe_failed.log`; real uv install failures still use `install_logs/uv_install_failed.log`.
- Documentation: Updated README to version 0.1.36.

## 0.1.35 - 2026-06-24

- Pygame education mode: Reworked the procedural scene renderer toward a stylized low-poly/cartoon-like look with layered terrain facets, decorative sky bodies, stronger depth cues and foreground shading.
- Pygame Earth scene: Tuned the forest overlook toward a warmer, more readable stylized outdoor palette with low-poly trees, bushes and a visible path/clearing.
- Pygame planet scenes: Added more distinctive stylized props for Mars-like mesas, Venus haze/fire strokes, icy Neptune-style shards and rocky/cratered surfaces.
- Documentation: Updated README and scientific limitation notes to clarify that the fullscreen mode is a playful educational visualization with fully procedural original visuals, not an observation planner or real terrain renderer.

## 0.1.34 - 2026-06-24

- 3D / Simulation: Added an optional scenario engine selector so **Play this scenario** can use either a fullscreen Pygame education mode or the lighter HTML/Plotly viewpoint fallback.
- Pygame mode: Added fullscreen launch, ESC exit, F11 fullscreen toggle, WASD/mouse movement, telescope toggle, mouse-wheel zoom, time-speed controls and an in-scene help overlay.
- Pygame mode: Added procedural ambience, footsteps and telescope-switch sound effects without bundling audio files. Earth uses forest-like ambience, Venus uses fire/haze-like ambience, Moon/airless bodies use low wind/suit-like ambience, and Neptune uses icy-wind ambience.
- Performance: Before launching the fullscreen Pygame scene, the app now tries to unload a keep-alive Ollama model to free RAM/VRAM for smoother rendering.
- Spacecraft catalog: Added a GUI tab for editing, saving, reloading and opening the local `data/spacecraft_regions.json` catalog.
- Ollama prompt hygiene: Reduced app-internal wording in the model context so Ollama focuses on CAD values, computed/context fields and the selected object rather than the application itself.
- Installer/dependencies: Pygame is now included in the normal dependency set so the optional education mode is available after standard installation when wheels are available.
- Documentation: Updated README and changelog for version 0.1.34.

## 0.1.33 - 2026-06-24

- Themes: Renamed the bundled Hellfire theme display name to exactly `Hellfire`.
- Themes: Tuned Aurora with stronger violet accents while keeping the teal/polar-light look.
- 3D / Simulation: Added a surface/flyby viewpoint HTML view with a viewpoint selector and a configurable time span around modeled closest approach.
- Viewpoint visualization: Target-surface mode shows an idealized sky path from the sub-approach point; flyby-object mode shows the target body as seen from the synthetic NEO trajectory.
- Documentation: Updated Usage Notes, README and scientific-limitations notes to clarify that the viewpoint view is CAD-derived and not a true Horizons/SPICE/geographic visibility calculation.

## 0.1.32 - 2026-06-24

- Review pass: Performed a broad static review across source files, installers, localization files, themes, data catalogs, and documentation.
- Diagnostics: Added a built-in app self-check for key files, language/theme consistency, spacecraft/probe catalog health, writable output folders, selected Ollama model state, and loaded CAD records.
- Table robustness: Selection and countdown refresh now use hidden per-record keys, improving reliability after sorting and with duplicate-looking close-approach rows.
- Ollama corrections: Added more defensive parsing for plain-text correction sentinels, one-line correction JSON, fenced JSON, and legacy APP_TABLE_CORRECTIONS blocks.
- Data safety: Configuration and CAD cache writes now use temporary files where practical; the previous CAD cache is preserved as a backup before replacement.
- Spacecraft catalog: User-edited catalog entries are validated more defensively, malformed entries are skipped with warnings, and built-in fallback regions are used if the catalog is missing or unusable.
- Ollama UX: Added explicit checks for an empty selected model before running initial analyses or follow-up questions.
- Shutdown: Text-to-speech is stopped before model-unload cleanup during app close.
- Installer: Wheelhouse downloads now use the same progress-suppression path as normal pip operations to reduce noisy console glyphs.
- Usage Notes: Refreshed and localized usage notes, including self-check, spacecraft/probe context, app-derived values, LLM corrections, and Ollama keep-alive behavior.
- Scientific documentation: Expanded `docs/SCIENTIFIC_LIMITATIONS.md` to cover app-derived risk/context fields and the local spacecraft/probe catalog.
- Documentation: Updated README to version 0.1.32 and kept release history in this changelog.

## v0.1.31

- Data table: Reworked the former satellite-only note into a broader spacecraft/probe context field.
- Spacecraft context: Added an editable local `data/spacecraft_regions.json` catalog of approximate artificial-object regions, including Earth satellite shells, cislunar space, Sun-Earth L1/L2 distance shells, lunar mission regions and selected planet-orbiter system shells.
- Analysis context: Ollama now receives the local spacecraft/probe-region catalog match details and is instructed to treat them as broad screening context, not as live ephemeris/conjunction proof.
- Options: Added a toggle for enabling or disabling the local spacecraft/probe context catalog.
- Usage Notes: Added localized explanation of the spacecraft/probe context field and its limits.
- Documentation: Updated README to version 0.1.31 and documented the local catalog file.

## 0.1.30 - 2026-06-24

- Ollama: Fixed a possible HTTP 400 Bad Request on `/api/generate` caused by incompatible `keep_alive` values on some Ollama versions.
- Ollama: The keep-alive request now uses the broadly compatible duration string `24h`; explicit unload uses `keep_alive: "0"`.
- Ollama: If a build rejects keep_alive, the client retries the same generate request once without keep_alive instead of failing immediately.
- Diagnostics: HTTP errors from Ollama now include the response body when available, making future 400-level errors easier to identify.
- Documentation: Updated README to version 0.1.30.

## 0.1.29 - 2026-06-24

- Installer: The suggested shared PythonDepot/cache path is now automatically accepted after a 10-second timeout unless the user types another path.
- Installer: The selected depot/cache path is saved for subsequent setup actions such as the wheelhouse build.
- Installer: The normal install flow now offers to build/update the offline wheelhouse automatically after a 10-second skip window.
- Installer: build_wheelhouse_windows.bat now supports automated invocation without pausing at the end.
- Documentation: Updated README to version 0.1.29 and documented the timeout-based installer defaults.

## 0.1.28 - 2026-06-24

- Ollama performance: Added a keep-alive option so the selected local model can remain loaded between analyses and follow-up questions, reducing repeated cold-load delays.
- Options: Added a manual button to unload the selected Ollama model from RAM/VRAM when memory should be released.
- Shutdown: When model keep-alive is enabled, the app asks Ollama to unload the selected model while closing.
- Themes: Added the new Aurora theme with dark polar-light colors and teal/violet highlights.
- 3D visualization: Added Aurora palette support for generated HTML visualizations.
- Usage Notes: Added a localized note explaining Ollama model memory/keep-alive behavior.
- Documentation: Updated README to version 0.1.28 and kept it publication-oriented.

## 0.1.27 - 2026-06-23

- Ollama: Prompt now tells local models to keep long recurring CAD/simulation limitation and generic verification sections out of the main analysis text; these belong in Usage Notes.
- Ollama: Added post-processing that removes common boilerplate limitation/verification sections from visible answers while preserving the object article and technical assessment.
- Ollama: Table-correction prompt now asks for an empty machine-readable correction block when no correction is needed, so the GUI can distinguish “no corrections” from a missing block.
- UI: Added a small LLM correction status label next to the manual apply button, showing whether corrections are pending, absent, applied, or disabled.
- Usage Notes: Added an Ollama-specific note section explaining why recurring caveats are documented there rather than repeated in every answer.
- Documentation: Updated README to version 0.1.27 and kept it publication-oriented.

## 0.1.26 - 2026-06-23

- Ollama: Updated the selected-record analysis prompt to include an additional short article-style prose section before the technical assessment.
- Ollama: The new article section is intended to be generally understandable, comparison-rich, calm in tone, and additive to the existing scientific analysis rather than replacing it.
- Documentation: Updated README to version 0.1.26 and kept it publication-oriented.

## v0.1.25

- Data table: Restored reliable click-to-sort behavior for all table headers after the custom app-derived header coloring change.
- Data table: Header coloring now overlays the native Qt header instead of replacing it completely, preserving normal clickable/sortable header behavior and sort indicators.
- Documentation: Updated README to version 0.1.25 and kept it publication-oriented.

## v0.1.24

- Data table: Reworked app-derived header coloring using a custom header view so derived-column headers remain visibly different even under strong themes such as Hellfire.
- Data table: Added CSV export for the currently visible table.
- Ollama: Changed LLM table corrections from automatic application to a manual review/apply flow with an explicit button.
- Ollama: Pending LLM corrections are stored until the user applies them; CAD/API columns are still not overwritten.
- Risk model: Revised the local Risk score to represent the current close-approach encounter rather than a MOID/PHA-style long-term orbital hazard score.
- Impact proxy: Avoids misleading Gaussian tails when the CAD lower distance bound remains outside the target-body radius.
- Usage Notes: Expanded formula explanations for column source coloring, current encounter score, impact proxy, CSV export, and manual LLM correction application.
- Documentation: Updated README to version 0.1.24 and kept it publication-oriented.

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
