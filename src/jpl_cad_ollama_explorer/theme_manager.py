# source: https://github.com/zeittresor
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtWidgets import QApplication


@dataclass(slots=True)
class ThemeInfo:
    theme_id: str
    display_name: str
    description: str
    qss: str


class ThemeManager:
    def __init__(self, theme_dir: Path) -> None:
        self.theme_dir = theme_dir
        self.themes: dict[str, ThemeInfo] = {}
        self.load_themes()

    def load_themes(self) -> None:
        self.themes.clear()
        for path in sorted(self.theme_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                theme = ThemeInfo(
                    theme_id=str(data.get("id") or path.stem),
                    display_name=str(data.get("display_name") or path.stem),
                    description=str(data.get("description") or ""),
                    qss=str(data.get("qss") or ""),
                )
                self.themes[theme.theme_id] = theme
            except Exception:
                continue
        if not self.themes:
            self.themes["dark"] = ThemeInfo("dark", "Dark", "Built-in fallback", "")

    def names(self) -> list[tuple[str, str]]:
        return [(theme_id, info.display_name) for theme_id, info in self.themes.items()]

    def apply(self, app: QApplication, theme_id: str) -> None:
        theme = self.themes.get(theme_id) or next(iter(self.themes.values()))
        app.setStyleSheet(theme.qss)
