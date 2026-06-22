# source: https://github.com/zeittresor
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import socket
import struct
import time


NTP_DELTA = 2_208_988_800  # Seconds between 1900-01-01 and Unix epoch.
DEFAULT_NTP_HOSTS = ("time.cloudflare.com", "time.google.com", "pool.ntp.org")


@dataclass(slots=True)
class NetworkTimeStatus:
    online: bool
    checked_at_utc: str
    source: str
    utc_time: str
    latency_ms: float | None = None
    error: str = ""

    def compact(self) -> str:
        state = "online" if self.online else "offline/unknown"
        latency = "" if self.latency_ms is None else f", latency={self.latency_ms:.0f} ms"
        err = "" if not self.error else f", error={self.error}"
        return f"network={state}, source={self.source}, utc={self.utc_time}{latency}{err}"


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _query_ntp(host: str, timeout_seconds: float) -> tuple[str, float]:
    packet = b"\x1b" + 47 * b"\0"
    started = time.perf_counter()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout_seconds)
        sock.sendto(packet, (host, 123))
        data, _ = sock.recvfrom(48)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if len(data) < 48:
        raise RuntimeError("short NTP response")
    seconds = struct.unpack("!12I", data[:48])[10]
    unix_seconds = seconds - NTP_DELTA
    utc_time = datetime.fromtimestamp(unix_seconds, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return utc_time, elapsed_ms


def check_network_time(timeout_seconds: float = 2.5, hosts: tuple[str, ...] = DEFAULT_NTP_HOSTS) -> NetworkTimeStatus:
    checked_at = _now_utc_iso()
    errors: list[str] = []
    for host in hosts:
        try:
            utc_time, latency_ms = _query_ntp(host, timeout_seconds)
            return NetworkTimeStatus(True, checked_at, f"NTP:{host}", utc_time, latency_ms, "")
        except Exception as exc:
            errors.append(f"{host}: {exc}")
    # Fallback is intentionally explicit: system clock can still be useful as temporal context,
    # but it is not proof of internet reachability.
    return NetworkTimeStatus(False, checked_at, "system-clock-fallback", checked_at, None, "; ".join(errors[-2:]))
