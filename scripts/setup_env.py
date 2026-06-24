# source: https://github.com/zeittresor
from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
REQ = ROOT / "requirements.txt"
WHEELHOUSE = ROOT / "wheelhouse"
LOG_DIR = ROOT / "install_logs"
DEPOT_CHOICE_FILE = LOG_DIR / "last_python_depot.txt"

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
        "orange": "\033[38;2;255;165;0m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m",
    }
    return colors.get(fg, colors["white"]) + text + colors["reset"]


def _windows_console_handle():
    if os.name != "nt" or not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return None
    try:
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(_STD_OUTPUT_HANDLE)
        if handle in (0, -1):
            return None
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return None
        return handle
    except Exception:
        return None


def _windows_console_attr(handle):
    class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.c_short * 2),
            ("dwCursorPosition", ctypes.c_short * 2),
            ("wAttributes", ctypes.c_ushort),
            ("srWindow", ctypes.c_short * 4),
            ("dwMaximumWindowSize", ctypes.c_short * 2),
        ]
    try:
        info = CONSOLE_SCREEN_BUFFER_INFO()
        if ctypes.windll.kernel32.GetConsoleScreenBufferInfo(handle, ctypes.byref(info)):  # type: ignore[attr-defined]
            return int(info.wAttributes)
    except Exception:
        pass
    return 0x07


def _windows_fg_attr(fg: str) -> int:
    # Legacy Windows console has no true orange. 0x06 is the closest readable
    # orange/brown warning color on dark backgrounds; modern VT consoles use
    # the RGB ANSI orange defined in color().
    return {
        "red": 0x0C,
        "green": 0x0A,
        "yellow": 0x0E,
        "orange": 0x06,
        "blue": 0x09,
        "magenta": 0x0D,
        "cyan": 0x0B,
        "white": 0x0F,
    }.get(fg, 0x0F)


def print_colored(text: str, fg: str = "white", *, end: str = "\n") -> None:
    if supports_ansi():
        print(color(text, fg), end=end)
        return
    handle = _windows_console_handle()
    if handle is None:
        print(text, end=end)
        return
    old_attr = _windows_console_attr(handle)
    try:
        ctypes.windll.kernel32.SetConsoleTextAttribute(handle, _windows_fg_attr(fg))  # type: ignore[attr-defined]
        print(text, end=end)
    finally:
        try:
            ctypes.windll.kernel32.SetConsoleTextAttribute(handle, old_attr)  # type: ignore[attr-defined]
        except Exception:
            pass


def print_status(tag: str, fg: str, message: str = "") -> None:
    prefix = f"[{tag}] "
    if supports_ansi():
        print(color(prefix, fg) + message)
        return
    handle = _windows_console_handle()
    if handle is None:
        print(prefix + message)
        return
    old_attr = _windows_console_attr(handle)
    try:
        ctypes.windll.kernel32.SetConsoleTextAttribute(handle, _windows_fg_attr(fg))  # type: ignore[attr-defined]
        sys.stdout.write(prefix)
        sys.stdout.flush()
    finally:
        try:
            ctypes.windll.kernel32.SetConsoleTextAttribute(handle, old_attr)  # type: ignore[attr-defined]
        except Exception:
            pass
    print(message)


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
    print_status("CMD", "cyan", " ".join(str(part) for part in cmd))
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



def timed_input_with_default(prompt: str, default: Path, timeout_seconds: int = 10) -> str:
    """Read one line with a timeout, returning empty string for default.

    On Windows this uses msvcrt so a user can start typing before the timeout
    and then finish the path normally. On non-interactive or redirected input,
    the default is selected immediately so installers do not hang.
    """
    if timeout_seconds <= 0 or not sys.stdin.isatty():
        print(prompt + str(default))
        return ""

    print(prompt, end="", flush=True)
    if os.name == "nt":
        try:
            import msvcrt  # type: ignore[import-not-found]
        except Exception:
            try:
                return input().strip()
            except EOFError:
                return ""

        chars: list[str] = []
        deadline = time.monotonic() + timeout_seconds
        typing_started = False
        while typing_started or time.monotonic() < deadline:
            if msvcrt.kbhit():
                typing_started = True
                ch = msvcrt.getwch()
                if ch in {"\r", "\n"}:
                    print()
                    return "".join(chars).strip()
                if ch == "\x03":
                    raise KeyboardInterrupt
                if ch in {"\b", "\x7f"}:
                    if chars:
                        chars.pop()
                        print("\b \b", end="", flush=True)
                    continue
                # Ignore navigation/function-key prefixes and other control chars.
                if ch in {"\x00", "\xe0"}:
                    if msvcrt.kbhit():
                        msvcrt.getwch()
                    continue
                if ord(ch) >= 32:
                    chars.append(ch)
                    print(ch, end="", flush=True)
            else:
                time.sleep(0.05)
        print(str(default))
        return ""

    try:
        import select
        ready, _, _ = select.select([sys.stdin], [], [], timeout_seconds)
        if ready:
            return sys.stdin.readline().strip()
        print(str(default))
        return ""
    except Exception:
        try:
            return input().strip()
        except EOFError:
            return ""

def prompt_depot(non_interactive: bool = False) -> Path:
    default = best_depot_path()
    try:
        saved = DEPOT_CHOICE_FILE.read_text(encoding="utf-8").strip()
        if saved:
            default = Path(saved)
    except OSError:
        pass
    print_status("INFO", "blue", f"Suggested shared Python depot/cache path: {default}")
    if non_interactive:
        depot = default
        print_status("AUTO", "green", f"Using suggested depot/cache path: {depot}")
    else:
        try:
            value = timed_input_with_default(
                "Depot/cache path [press Enter for suggested path; auto-selects in 10s]: ",
                default,
                timeout_seconds=10,
            ).strip().strip('"')
        except EOFError:
            value = ""
        depot = Path(value) if value else default
        if not value:
            print_status("AUTO", "green", f"Using suggested depot/cache path: {depot}")
    depot.mkdir(parents=True, exist_ok=True)
    for sub in ["uv_cache", "pip_cache", "downloads", "logs", "tools", "wheelhouse"]:
        (depot / sub).mkdir(parents=True, exist_ok=True)
    try:
        LOG_DIR.mkdir(exist_ok=True)
        DEPOT_CHOICE_FILE.write_text(str(depot), encoding="utf-8")
    except OSError:
        pass
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
        print_status("OK", "green", f"Using existing venv: {VENV}")
        return
    print_status("STEP", "magenta", f"Creating project-local venv: {VENV}")
    run([sys.executable, "-m", "venv", str(VENV)])


def sanity_check_python(py: str, env: dict[str, str]) -> bool:
    result = run([py, "-c", "import sys, encodings; print(sys.executable); print(sys.prefix)"], env=env, check=False)
    if result.returncode != 0:
        print_status("WARN", "orange", "The venv Python interpreter failed a sanity check.")
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
        print_status("OK", "green", f"Managed uv available: {uv_path}" + (f" ({version})" if version else ""))
        return True
    log_file = log_optional_failure("managed_uv_version_failed.log", result.stdout or "uv --version failed")
    print_status("WARN", "orange", f"Managed uv exists but did not run; details written to {log_file}")
    return False


def install_managed_uv(depot: Path, env: dict[str, str], *, offline: bool = False) -> Path | None:
    """Prepare a shared uv installation under the selected Python depot.

    This is deliberately best-effort. A broken or unavailable uv must never
    prevent the app from installing, because normal venv pip is the safe path.
    """
    if os.environ.get("JPL_CAD_SKIP_MANAGED_UV", "").lower() in {"1", "true", "yes", "on"}:
        print_status("INFO", "blue", "JPL_CAD_SKIP_MANAGED_UV is set; not preparing depot-managed uv.")
        return None

    uv_path = managed_uv_exe(depot)
    if check_uv(uv_path, env):
        return uv_path

    uv_py = managed_uv_python(depot)
    uv_home = managed_uv_dir(depot)
    print_status("STEP", "magenta", f"Preparing depot-managed uv: {uv_home}")

    try:
        if not uv_py.exists():
            run([sys.executable, "-m", "venv", str(uv_home)], env=env, check=True)
        result = pip_install(str(uv_py), ["install", "--upgrade", "pip", "setuptools", "wheel"], env, check=False, capture=True)
        if result.returncode != 0:
            log_file = log_optional_failure("managed_uv_bootstrap_failed.log", result.stdout or "managed uv bootstrap failed")
            print_status("WARN", "orange", f"Could not bootstrap managed uv venv; details written to {log_file}")
            return None

        uv_args = ["install", "--upgrade"]
        if offline:
            if not WHEELHOUSE.exists():
                print_status("WARN", "orange", "Offline mode and no wheelhouse/ exists; cannot prepare managed uv offline.")
                return None
            uv_args.extend(["--no-index", "--find-links", str(WHEELHOUSE)])
        uv_args.append("uv")
        result = pip_install(str(uv_py), uv_args, env, check=False, capture=True)
        if result.returncode != 0:
            log_file = log_optional_failure("managed_uv_install_failed.log", result.stdout or "managed uv install failed")
            print_status("WARN", "orange", f"Could not install managed uv; details written to {log_file}")
            return None
    except Exception as exc:
        log_file = log_optional_failure("managed_uv_exception.log", repr(exc))
        print_status("WARN", "orange", f"Could not prepare managed uv; details written to {log_file}")
        return None

    if check_uv(uv_path, env):
        return uv_path
    return None


def choose_uv(depot: Path, env: dict[str, str], *, offline: bool = False) -> str | None:
    # JPL_CAD_NO_UV disables all uv use. JPL_CAD_SKIP_MANAGED_UV only skips the
    # depot-managed install and still permits an already global uv.
    uv_disabled = os.environ.get("JPL_CAD_NO_UV", "").lower() in {"1", "true", "yes", "on"}
    if uv_disabled:
        print_status("INFO", "blue", "JPL_CAD_NO_UV is set; using pip fallback.")
        return None

    managed = install_managed_uv(depot, env, offline=offline)
    if managed:
        return str(managed)

    global_uv = shutil.which("uv")
    if global_uv:
        print_status("INFO", "blue", f"Using global uv fallback if it works: {global_uv}")
        return global_uv

    print_status("WARN", "orange", "uv not available; using pip fallback.")
    return None


def install_requirements(depot: Path, env: dict[str, str], offline: bool = False) -> None:
    py = str(venv_python())
    if not sanity_check_python(py, env):
        print_status("STEP", "magenta", "Recreating broken venv.")
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
        print_status("INFO", "blue", f"Trying uv accelerator: {uv}")
        result = run([uv, "--no-progress", "--color", "never", "pip", "install", "--python", py, "-r", str(REQ)], env=env, check=False, capture=True)
        if result.returncode == 0:
            if result.stdout:
                print(result.stdout.rstrip())
            return
        log_file = log_optional_failure("uv_install_failed.log", result.stdout or "uv failed without output")
        print_status("WARN", "orange", f"uv install failed; details written to {log_file}")
        print_status("WARN", "orange", "Retrying with venv pip fallback.")

    if WHEELHOUSE.exists():
        pip_install(py, ["install", "--find-links", str(WHEELHOUSE), "-r", str(REQ)], env)
    else:
        pip_install(py, ["install", "-r", str(REQ)], env)


def build_wheelhouse(env: dict[str, str]) -> None:
    WHEELHOUSE.mkdir(exist_ok=True)
    py = str(venv_python())
    pip_install(py, ["download", "-r", str(REQ), "-d", str(WHEELHOUSE)], env)
    # Include uv itself so an offline machine can prepare the depot-managed uv
    # tool from wheelhouse/ instead of needing a live download.
    pip_install(py, ["download", "uv", "-d", str(WHEELHOUSE)], env)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["install", "offline", "wheelhouse"], default="install")
    parser.add_argument("--non-interactive", action="store_true")
    args = parser.parse_args()
    print_colored("=" * 72, "cyan")
    print_colored("JPL CAD Ollama Explorer setup", "cyan")
    print_colored("=" * 72, "cyan")
    depot = prompt_depot(args.non_interactive)
    env = build_env(depot)
    ensure_venv()
    if args.mode == "wheelhouse":
        install_requirements(depot, env, offline=False)
        build_wheelhouse(env)
    else:
        install_requirements(depot, env, offline=args.mode == "offline")
    print_status("OK", "green", "Setup complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
