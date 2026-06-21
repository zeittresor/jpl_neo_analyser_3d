# source: https://github.com/zeittresor
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from urllib.parse import urlencode

import requests

CAD_API_URL = "https://ssd-api.jpl.nasa.gov/cad.api"
OLLAMA_DEFAULT_URL = "http://localhost:11434"


class CadApiError(RuntimeError):
    pass


@dataclass(slots=True)
class CadQuery:
    date_min: str = "now"
    date_max: str = "+60"
    dist_max: str = "0.05"
    body: str = "Earth"
    sort: str = "date"
    limit: int = 100
    des: str = ""
    orbit_class: str = ""
    h_min: str = ""
    h_max: str = ""
    v_rel_min: str = ""
    v_rel_max: str = ""
    neo: bool = True
    pha: bool = False
    nea: bool = False
    comet: bool = False
    diameter: bool = True
    fullname: bool = True

    def to_params(self) -> dict[str, str]:
        params: dict[str, str] = {}
        specific_object = bool(self.des.strip())
        if self.date_min:
            params["date-min"] = self.date_min
        if self.date_max:
            params["date-max"] = self.date_max
        if self.dist_max:
            params["dist-max"] = self.dist_max
        if self.body:
            params["body"] = self.body
        if self.sort:
            params["sort"] = self.sort
        if self.limit and self.limit > 0:
            params["limit"] = str(self.limit)
        if self.des.strip():
            params["des"] = self.des.strip()

        # JPL CAD rejects category/filter parameters such as neo when a
        # specific object is requested via des/spk. Keep the GUI state intact,
        # but silently omit incompatible filters from the API request.
        if not specific_object:
            if self.orbit_class.strip():
                params["class"] = self.orbit_class.strip()
            if self.h_min.strip():
                params["h-min"] = self.h_min.strip()
            if self.h_max.strip():
                params["h-max"] = self.h_max.strip()
            if self.v_rel_min.strip():
                params["v-rel-min"] = self.v_rel_min.strip()
            if self.v_rel_max.strip():
                params["v-rel-max"] = self.v_rel_max.strip()
            # CAD boolean filters are only applied when true. neo=false disables the default NEO filter.
            params["neo"] = "true" if self.neo else "false"
            if self.pha:
                params["pha"] = "true"
            if self.nea:
                params["nea"] = "true"
            if self.comet:
                params["comet"] = "true"
        if self.diameter:
            params["diameter"] = "true"
        if self.fullname:
            params["fullname"] = "true"
        return params

    def url(self) -> str:
        return f"{CAD_API_URL}?{urlencode(self.to_params())}"


class CadApiClient:
    def __init__(self, timeout_seconds: int = 30) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch(self, query: CadQuery) -> dict[str, Any]:
        response = requests.get(CAD_API_URL, params=query.to_params(), timeout=self.timeout_seconds)
        if response.status_code != 200:
            try:
                payload = response.json()
                message = payload.get("message") or payload.get("error") or response.text
            except Exception:
                message = response.text
            raise CadApiError(f"JPL CAD API error {response.status_code}: {message}")
        try:
            payload: dict[str, Any] = response.json()
        except ValueError as exc:
            raise CadApiError(f"JPL CAD API did not return JSON: {exc}") from exc
        if "message" in payload and not payload.get("data"):
            raise CadApiError(str(payload["message"]))
        return payload


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_DEFAULT_URL, timeout_seconds: int = 600) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def list_models(self) -> list[str]:
        response = requests.get(f"{self.base_url}/api/tags", timeout=15)
        response.raise_for_status()
        payload = response.json()
        models = payload.get("models", [])
        return [m.get("name", "") for m in models if m.get("name")]

    def generate(self, model: str, prompt: str, temperature: float = 0.2, num_ctx: int = 8192) -> str:
        """Generate text via Ollama using streaming mode.

        The UI still receives the final text only, but streaming prevents long
        non-streaming responses from looking like a dead HTTP connection. The
        timeout is a read-inactivity timeout, not a hard total runtime limit.
        """
        data = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
            },
        }
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=data,
                timeout=(10, self.timeout_seconds),
                stream=True,
            )
            response.raise_for_status()
            parts: list[str] = []
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if payload.get("error"):
                    raise RuntimeError(str(payload["error"]))
                if "response" in payload:
                    parts.append(str(payload.get("response", "")))
                if payload.get("done"):
                    break
            return "".join(parts).strip()
        except requests.exceptions.ReadTimeout as exc:
            raise RuntimeError(
                f"Ollama did not return data for {self.timeout_seconds} seconds. "
                "The model may still be loading or the request may be too heavy. "
                "Increase the Ollama timeout in the UI, choose a smaller model, reduce context tokens, "
                "or try a short test prompt first."
            ) from exc
        except requests.exceptions.ConnectTimeout as exc:
            raise RuntimeError(
                "Could not connect to Ollama in time. Check whether Ollama is running and whether the URL is correct."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                "Could not connect to Ollama. Check whether Ollama is running at the configured URL."
            ) from exc
