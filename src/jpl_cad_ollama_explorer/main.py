# source: https://github.com/zeittresor
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from .i18n import Translator
from .theme_manager import ThemeManager
from .ui import MainWindow


def project_root() -> Path:
    # Works both from source tree and installed package when launched from app.py.
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "themes").exists() and (parent / "lang").exists():
            return parent
    return Path.cwd()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("JPL CAD Ollama Explorer")
    root = project_root()
    translator = Translator(root / "lang", "en")
    theme_manager = ThemeManager(root / "themes")
    window = MainWindow(app, root, translator, theme_manager)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
