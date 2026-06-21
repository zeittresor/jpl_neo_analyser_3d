# source: https://github.com/zeittresor
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Translator:
    def __init__(self, lang_dir: Path, language: str = "en") -> None:
        self.lang_dir = lang_dir
        self.language = language
        self._data: dict[str, str] = {}
        self.load(language)

    def available_languages(self) -> list[str]:
        if not self.lang_dir.exists():
            return ["en"]
        langs = sorted(path.stem for path in self.lang_dir.glob("*.json"))
        return langs or ["en"]

    def load(self, language: str) -> None:
        self.language = language
        path = self.lang_dir / f"{language}.json"
        fallback_path = self.lang_dir / "en.json"
        data: dict[str, Any] = {}
        if fallback_path.exists():
            data.update(json.loads(fallback_path.read_text(encoding="utf-8")))
        if path.exists() and path != fallback_path:
            data.update(json.loads(path.read_text(encoding="utf-8")))
        self._data = {str(k): str(v) for k, v in data.items()}

    def t(self, key: str) -> str:
        return self._data.get(key, key)
