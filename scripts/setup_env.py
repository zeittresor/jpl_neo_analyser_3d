# source: https://github.com/zeittresor
from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
REQ = ROOT / "requirements.txt"
WHEELHOUSE = ROOT / "wheelhouse"
LOG_DIR = ROOT / "install_logs"

_ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
_STD_OUTPUT_HANDLE = -11
_ANSI_ENABLED: bool | None = None


def _enable_windows_vt_mode() -> bool:
    """Enable ANSI colors in old Windows consoles when possible.

    Some Windows hosts print raw escape codes unless Virtual Terminal
    Processing is explicitly enabled. If enabling it fails, the installer
    falls back to plain readable text instead of leaking ANSI sequences.
    """
    if os.name != "nt":
        return True
    if not sys.stdout.isatty():
        return False
    try:
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(_STD_OUTPUT_HANDLE)
        if handle in (0, -1):
            return False
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        if mode.value & _ENABLE_VIRTUAL_TERMINAL_PROCESSING:
            return True
        return bool(kernel32.SetConsoleMode(handle, mode.value | _ENABLE_VIRTUAL_TERMINAL_PROCESSING))
    except Exception:
        return False


def supports_ansi() -> bool:
    global _ANSI_ENABLED
    if os.environ.get("NO_COLOR"):
        return False
    if _ANSI_ENABLED is None:
        _ANSI_ENABLED = bool(sys.stdout.isatty() and _enable_windows_vt_mode())
    return _ANSI_ENABLED


def color(text: str, fg: str = "white") -> str:
    if not supports_ansi():
        return text
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m",
    }
    return colors.get(fg, colors["white"]) + text + colors["reset"]


def log_optional_failure(name: str, output: str) -> Path:
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / name
    log_file.write_text(output or "command failed without output", encoding="utf-8", errors="replace")
    return log_file


def run(
    cmd: list[str],
    env: dict[str, str] | None = None,
    *,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    print(color("[CMD] ", "cyan") + " ".join(str(part) for part in cmd))
    if capture:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    else:
        result = subprocess.run(cmd, cwd=ROOT, env=env)
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def managed_uv_dir(depot: Path) -> Path:
    return depot / "tools" / "uv_venv"


def managed_uv_python(depot: Path) -> Path:
    if os.name == "nt":
        return managed_uv_dir(depot) / "Scripts" / "python.exe"
    return managed_uv_dir(depot) / "bin" / "python"


def managed_uv_exe(depot: Path) -> Path:
    if os.name == "nt":
        return managed_uv_dir(depot) / "Scripts" / "uv.exe"
    return managed_uv_dir(depot) / "bin" / "uv"


def best_depot_path() -> Path:
    if os.name != "nt":
        return ROOT / "PythonDepot"
    best = None
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZC":
        drive = Path(f"{letter}:\\")
        if not drive.exists():
            continue
        try:
            usage = shutil.disk_usage(drive)
        except OSError:
            continue
        if best is None or usage.free > best[0]:
            best = (usage.free, drive)
    drive = best[1] if best else Path("C:\\")
    return drive / "PythonDepot"


def prompt_depot(non_interactive: bool = False) -> Path:
    default = best_depot_path()
    print(color("[INFO] ", "blue") + f"Suggested shared Python depot/cache path: {default}")
    if non_interactive:
        depot = default
    else:
        try:
            value = input("Depot/cache path [press Enter for suggested path]: ").strip().strip('"')
        except EOFError:
            value = ""
        depot = Path(value) if value else default
    depot.mkdir(parents=True, exist_ok=True)
    for sub in ["uv_cache", "pip_cache", "downloads", "logs", "tools", "wheelhouse"]:
        (depot / sub).mkdir(parents=True, exist_ok=True)
    return depot


def build_env(depot: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(depot / "uv_cache")
    env["PIP_CACHE_DIR"] = str(depot / "pip_cache")
    # Keep subprocess output readable in older Windows consoles. Newer pip/uv
    # versions may use Unicode progress bars such as box-drawing glyphs; on
    # legacy hosts those can appear as question marks even though copy/paste
    # preserves the real characters. Disable progress bars for installer work.
    env["PIP_PROGRESS_BAR"] = "off"
    env["PIP_NO_COLOR"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["UV_NO_PROGRESS"] = "1"
    env["UV_COLOR"] = "never"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def ensure_venv() -> None:
    if venv_python().exists():
        print(color("[OK] ", "green") + f"Using existing venv: {VENV}")
        return
    print(color("[STEP] ", "magenta") + f"Creating project-local venv: {VENV}")
    run([sys.executable, "-m", "venv", str(VENV)])


def sanity_check_python(py: str, env: dict[str, str]) -> bool:
    result = run([py, "-c", "import sys, encodings; print(sys.executable); print(sys.prefix)"], env=env, check=False)
    if result.returncode != 0:
        print(color("[WARN] ", "yellow") + "The venv Python interpreter failed a sanity check.")
        return False
    return True


def pip_args_without_progress(args: list[str]) -> list[str]:
    if not args:
        return args
    command = args[0]
    if command in {"install", "download", "wheel"} and "--progress-bar" not in args:
        return [command, "--progress-bar", "off", *args[1:]]
    return args


def pip_install(py: str, args: list[str], env: dict[str, str], *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    return run([py, "-m", "pip", *pip_args_without_progress(args)], env=env, check=check, capture=capture)


def check_uv(uv_path: Path, env: dict[str, str]) -> bool:
    if not uv_path.exists():
        return False
    result = run([str(uv_path), "--version"], env=env, check=False, capture=True)
    if result.returncode == 0:
        version = (result.stdout or "").strip()
        print(color("[OK] ", "green") + f"Managed uv available: {uv_path}" + (f" ({version})" if version else ""))
        return True
    log_file = log_optional_failure("managed_uv_version_failed.log", result.stdout or "uv --version failed")
    print(color("[WARN] ", "yellow") + f"Managed uv exists but did not run; details written to {log_file}")
    return False


def install_managed_uv(depot: Path, env: dict[str, str], *, offline: bool = False) -> Path | None:
    """Prepare a shared uv installation under the selected Python depot.

    This is deliberately best-effort. A broken or unavailable uv must never
    prevent the app from installing, because normal venv pip is the safe path.
    """
    if os.environ.get("JPL_CAD_SKIP_MANAGED_UV", "").lower() in {"1", "true", "yes", "on"}:
        print(color("[INFO] ", "blue") + "JPL_CAD_SKIP_MANAGED_UV is set; not preparing depot-managed uv.")
        return None

    uv_path = managed_uv_exe(depot)
    if check_uv(uv_path, env):
        return uv_path

    uv_py = managed_uv_python(depot)
    uv_home = managed_uv_dir(depot)
    print(color("[STEP] ", "magenta") + f"Preparing depot-managed uv: {uv_home}")

    try:
        if not uv_py.exists():
            run([sys.executable, "-m", "venv", str(uv_home)], env=env, check=True)
        result = pip_install(str(uv_py), ["install", "--upgrade", "pip", "setuptools", "wheel"], env, check=False, capture=True)
        if result.returncode != 0:
            log_file = log_optional_failure("managed_uv_bootstrap_failed.log", result.stdout or "managed uv bootstrap failed")
            print(color("[WARN] ", "yellow") + f"Could not bootstrap managed uv venv; details written to {log_file}")
            return None

        uv_args = ["install", "--upgrade"]
        if offline:
            if not WHEELHOUSE.exists():
                print(color("[WARN] ", "yellow") + "Offline mode and no wheelhouse/ exists; cannot prepare managed uv offline.")
                return None
            uv_args.extend(["--no-index", "--find-links", str(WHEELHOUSE)])
        uv_args.append("uv")
        result = pip_install(str(uv_py), uv_args, env, check=False, capture=True)
        if result.returncode != 0:
            log_file = log_optional_failure("managed_uv_install_failed.log", result.stdout or "managed uv install failed")
            print(color("[WARN] ", "yellow") + f"Could not install managed uv; details written to {log_file}")
            return None
    except Exception as exc:
        log_file = log_optional_failure("managed_uv_exception.log", repr(exc))
        print(color("[WARN] ", "yellow") + f"Could not prepare managed uv; details written to {log_file}")
        return None

    if check_uv(uv_path, env):
        return uv_path
    return None


def choose_uv(depot: Path, env: dict[str, str], *, offline: bool = False) -> str | None:
    # JPL_CAD_NO_UV disables all uv use. JPL_CAD_SKIP_MANAGED_UV only skips the
    # depot-managed install and still permits an already global uv.
    uv_disabled = os.environ.get("JPL_CAD_NO_UV", "").lower() in {"1", "true", "yes", "on"}
    if uv_disabled:
        print(color("[INFO] ", "blue") + "JPL_CAD_NO_UV is set; using pip fallback.")
        return None

    managed = install_managed_uv(depot, env, offline=offline)
    if managed:
        return str(managed)

    global_uv = shutil.which("uv")
    if global_uv:
        print(color("[INFO] ", "blue") + f"Using global uv fallback if it works: {global_uv}")
        return global_uv

    print(color("[WARN] ", "yellow") + "uv not available; using pip fallback.")
    return None


def install_requirements(depot: Path, env: dict[str, str], offline: bool = False) -> None:
    py = str(venv_python())
    if not sanity_check_python(py, env):
        print(color("[STEP] ", "magenta") + "Recreating broken venv.")
        if VENV.exists():
            shutil.rmtree(VENV)
        ensure_venv()
        py = str(venv_python())
        if not sanity_check_python(py, env):
            raise SystemExit("The project-local venv Python is not usable. Please check the selected Python installation.")

    pip_install(py, ["install", "--upgrade", "pip", "setuptools", "wheel"], env)
    if offline:
        if not WHEELHOUSE.exists():
            raise SystemExit("Offline install requested but wheelhouse/ does not exist.")
        # In offline mode, try to make depot-managed uv available from wheelhouse,
        # but keep app dependency installation on plain pip for maximum reliability.
        choose_uv(depot, env, offline=True)
        pip_install(py, ["install", "--no-index", "--find-links", str(WHEELHOUSE), "-r", str(REQ)], env)
        return

    # uv is treated as an optional accelerator, never as a hard dependency.
    # The preferred uv is the one managed inside the selected PythonDepot.
    # A global uv is only a fallback, and any failure returns to venv pip.
    uv = choose_uv(depot, env, offline=False)
    if uv:
        print(color("[INFO] ", "blue") + f"Trying uv accelerator: {uv}")
        result = run([uv, "--no-progress", "--color", "never", "pip", "install", "--python", py, "-r", str(REQ)], env=env, check=False, capture=True)
        if result.returncode == 0:
            if result.stdout:
                print(result.stdout.rstrip())
            return
        log_file = log_optional_failure("uv_install_failed.log", result.stdout or "uv failed without output")
        print(color("[WARN] ", "yellow") + f"uv install failed; details written to {log_file}")
        print(color("[WARN] ", "yellow") + "Retrying with venv pip fallback.")

    if WHEELHOUSE.exists():
        pip_install(py, ["install", "--find-links", str(WHEELHOUSE), "-r", str(REQ)], env)
    else:
        pip_install(py, ["install", "-r", str(REQ)], env)


def build_wheelhouse(env: dict[str, str]) -> None:
    WHEELHOUSE.mkdir(exist_ok=True)
    py = str(venv_python())
    run([py, "-m", "pip", "download", "-r", str(REQ), "-d", str(WHEELHOUSE)], env=env)
    # Include uv itself so an offline machine can prepare the depot-managed uv
    # tool from wheelhouse/ instead of needing a live download.
    run([py, "-m", "pip", "download", "uv", "-d", str(WHEELHOUSE)], env=env)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["install", "offline", "wheelhouse"], default="install")
    parser.add_argument("--non-interactive", action="store_true")
    args = parser.parse_args()
    print(color("=" * 72, "cyan"))
    print(color("JPL CAD Ollama Explorer setup", "cyan"))
    print(color("=" * 72, "cyan"))
    depot = prompt_depot(args.non_interactive)
    env = build_env(depot)
    ensure_venv()
    if args.mode == "wheelhouse":
        install_requirements(depot, env, offline=False)
        build_wheelhouse(env)
    else:
        install_requirements(depot, env, offline=args.mode == "offline")
    print(color("[OK] Setup complete.", "green"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
