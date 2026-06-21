# source: https://github.com/zeittresor
from __future__ import annotations

import html
import json
import os
import re
import subprocess
import tempfile
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, Generic, TypeVar

from PyQt6.QtCore import QThread, Qt, QTimer, pyqtSignal
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import __app_name__, __version__
from .analysis import build_ollama_prompt, fallback_analysis
from .api_client import CadApiClient, CadQuery, OllamaClient
from .cad_models import CadRecord, parse_cad_payload
from .constants import BODY_CODES, BODY_DISPLAY, ORBIT_CLASS_DESCRIPTIONS
from .i18n import Translator
from .simulator import SimulationSettings, simulate_close_approach
from .theme_manager import ThemeManager
from .visualization import create_visualization_html, open_html

T = TypeVar("T")


class Worker(QThread, Generic[T]):
    finished_ok = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, func: Callable[[], T]) -> None:
        super().__init__()
        self.func = func

    def run(self) -> None:
        try:
            self.finished_ok.emit(self.func())
        except Exception as exc:
            self.failed.emit(f"{exc}\n\n{traceback.format_exc()}")


class NumericItem(QTableWidgetItem):
    def __init__(self, text: str, numeric_value: float | None = None) -> None:
        super().__init__(text)
        self.numeric_value = numeric_value

    def __lt__(self, other: QTableWidgetItem) -> bool:
        if isinstance(other, NumericItem) and self.numeric_value is not None and other.numeric_value is not None:
            return self.numeric_value < other.numeric_value
        return super().__lt__(other)


class ErrorDetailsDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        title: str,
        message: str,
        details: str,
        log_path: Path | None = None,
        copy_label: str = "Copy details",
        save_label: str = "Save as...",
        ok_label: str = "OK",
        save_dialog_title: str = "Save error details",
    ) -> None:
        super().__init__(parent)
        self.details = details
        self.log_path = log_path
        self.save_dialog_title = save_dialog_title
        self.setWindowTitle(title)
        self.resize(980, 680)
        layout = QVBoxLayout(self)

        headline = QLabel(message)
        headline.setWordWrap(True)
        layout.addWidget(headline)

        self.details_edit = QTextEdit()
        self.details_edit.setReadOnly(True)
        self.details_edit.setPlainText(details)
        layout.addWidget(self.details_edit, 1)

        if log_path is not None:
            log_label = QLabel(f"Log file: {log_path}")
            log_label.setWordWrap(True)
            layout.addWidget(log_label)

        buttons = QHBoxLayout()
        self.copy_btn = QPushButton(copy_label)
        self.save_btn = QPushButton(save_label)
        self.ok_btn = QPushButton(ok_label)
        buttons.addWidget(self.copy_btn)
        buttons.addWidget(self.save_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.ok_btn)
        layout.addLayout(buttons)

        self.copy_btn.clicked.connect(self.copy_details)
        self.save_btn.clicked.connect(self.save_details)
        self.ok_btn.clicked.connect(self.accept)

    def copy_details(self) -> None:
        QApplication.clipboard().setText(self.details_edit.toPlainText())

    def save_details(self) -> None:
        suggested = str(self.log_path) if self.log_path else "error_details.txt"
        selected, _ = QFileDialog.getSaveFileName(self, self.save_dialog_title, suggested, "Text files (*.txt);;All files (*)")
        if selected:
            Path(selected).write_text(self.details_edit.toPlainText(), encoding="utf-8")


class MainWindow(QMainWindow):
    table_columns = [
        "Object",
        "Date TDB",
        "Body",
        "Distance LD",
        "Min LD",
        "Max LD",
        "Distance km",
        "v_rel km/s",
        "H",
        "Diameter",
        "Uncertainty",
        "Triage",
    ]

    def __init__(
        self,
        app: QApplication,
        root_dir: Path,
        translator: Translator,
        theme_manager: ThemeManager,
    ) -> None:
        super().__init__()
        self.app = app
        self.root_dir = root_dir
        self.translator = translator
        self.theme_manager = theme_manager
        self.records: list[CadRecord] = []
        self.current_worker: Worker | None = None
        self.config_path = self.root_dir / "config.json"
        self.output_dir = self.root_dir / "output" / "visualizations"
        self.log_dir = self.root_dir / "output" / "logs"
        self.analysis_request_id = 0
        self.active_ollama_request_id: int | None = None
        self.ollama_started_at = 0.0
        self.ollama_busy_base_message = ""
        self.analysis_markdown = ""
        self.chat_turns: list[tuple[str, str]] = []
        self.tts_process: subprocess.Popen | None = None
        self.tts_temp_file: Path | None = None
        self.tts_poll_timer = QTimer(self)
        self.tts_poll_timer.setInterval(500)
        self.tts_poll_timer.timeout.connect(self._poll_tts_process)
        self.ollama_elapsed_timer = QTimer(self)
        self.ollama_elapsed_timer.setInterval(1000)
        self.ollama_elapsed_timer.timeout.connect(self._update_ollama_elapsed_label)
        self.i18n_labels: dict[str, QLabel] = {}
        self.i18n_groups: dict[str, QGroupBox] = {}
        self.sim_default_active = True
        self.setWindowTitle(f"{__app_name__} v{__version__}")
        self.resize(1480, 920)
        self._build_ui()
        self._load_config()
        self._connect_signals()
        self._apply_texts()
        self._set_status(self.translator.t("status_ready"))

    def _label(self, key: str, fallback: str) -> QLabel:
        label = QLabel(fallback)
        self.i18n_labels[key] = label
        return label

    def _group(self, key: str, fallback: str) -> QGroupBox:
        group = QGroupBox(fallback)
        self.i18n_groups[key] = group
        return group

    def _translated_table_headers(self) -> list[str]:
        t = self.translator.t
        keys = [
            "col_object",
            "col_date_tdb",
            "col_body",
            "col_distance_ld",
            "col_min_ld",
            "col_max_ld",
            "col_distance_km",
            "col_vrel",
            "col_h",
            "col_diameter",
            "col_uncertainty",
            "col_triage",
        ]
        return [t(key) for key in keys]

    def _about_html(self) -> str:
        t = self.translator.t
        return f"""
            <h1>{__app_name__} v{__version__}</h1>
            <p><b>{t("about_purpose_label")}:</b> {t("about_purpose_text")}</p>
            <p><b>{t("about_source_label")}:</b> github.com/zeittresor</p>
            <p><b>{t("about_scientific_label")}:</b> {t("about_scientific_text")}</p>
            <p><b>{t("about_privacy_label")}:</b> {t("about_privacy_text")}</p>
            """

    def _default_sim_text(self) -> str:
        return self.translator.t("sim_default_text")

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        self.data_tab = QWidget()
        self.analysis_tab = QWidget()
        self.sim_tab = QWidget()
        self.options_tab = QWidget()
        self.about_tab = QWidget()
        self.tabs.addTab(self.data_tab, "Data")
        self.tabs.addTab(self.analysis_tab, "Ollama Analysis")
        self.tabs.addTab(self.sim_tab, "3D / Simulation")
        self.tabs.addTab(self.options_tab, "Options")
        self.tabs.addTab(self.about_tab, "About")

        self._build_data_tab()
        self._build_analysis_tab()
        self._build_sim_tab()
        self._build_options_tab()
        self._build_about_tab()

        bottom = QHBoxLayout()
        self.status_label = QLabel("Ready")
        bottom.addWidget(self.status_label, 1)
        self.open_output_btn = QPushButton("Open Output Folder")
        bottom.addWidget(self.open_output_btn)
        root.addLayout(bottom)

    def _build_data_tab(self) -> None:
        layout = QVBoxLayout(self.data_tab)
        filter_box = self._group("group_jpl_query", "JPL CAD Query")
        filter_grid = QGridLayout(filter_box)

        self.date_min_edit = QLineEdit("now")
        self.date_max_edit = QLineEdit("+60")
        self.dist_max_edit = QLineEdit("0.05")
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 5000)
        self.limit_spin.setValue(100)
        self.body_combo = QComboBox()
        for code in BODY_CODES:
            self.body_combo.addItem(f"{BODY_DISPLAY.get(code, code)} ({code})", code)
        self.sort_combo = QComboBox()
        for sort in ["date", "dist", "dist-min", "v-rel", "v-inf", "h", "object", "-date", "-dist"]:
            self.sort_combo.addItem(sort)
        self.des_edit = QLineEdit()
        self.class_combo = QComboBox()
        self.class_combo.addItem("Any", "")
        for code, desc in ORBIT_CLASS_DESCRIPTIONS.items():
            self.class_combo.addItem(f"{code} — {desc}", code)
        self.h_min_edit = QLineEdit()
        self.h_max_edit = QLineEdit()
        self.vrel_min_edit = QLineEdit()
        self.vrel_max_edit = QLineEdit()
        self.neo_check = QCheckBox("NEO filter")
        self.neo_check.setChecked(True)
        self.pha_check = QCheckBox("PHA only")
        self.nea_check = QCheckBox("NEA only")
        self.comet_check = QCheckBox("Comets only")
        self.diameter_check = QCheckBox("Include diameter")
        self.diameter_check.setChecked(True)
        self.fullname_check = QCheckBox("Include full name")
        self.fullname_check.setChecked(True)

        row = 0
        filter_grid.addWidget(self._label("label_date_min", "Date min"), row, 0)
        filter_grid.addWidget(self.date_min_edit, row, 1)
        filter_grid.addWidget(self._label("label_date_max", "Date max"), row, 2)
        filter_grid.addWidget(self.date_max_edit, row, 3)
        filter_grid.addWidget(self._label("label_distance_max", "Distance max"), row, 4)
        filter_grid.addWidget(self.dist_max_edit, row, 5)
        row += 1
        filter_grid.addWidget(self._label("label_body", "Body"), row, 0)
        filter_grid.addWidget(self.body_combo, row, 1)
        filter_grid.addWidget(self._label("label_sort", "Sort"), row, 2)
        filter_grid.addWidget(self.sort_combo, row, 3)
        filter_grid.addWidget(self._label("label_limit", "Limit"), row, 4)
        filter_grid.addWidget(self.limit_spin, row, 5)
        row += 1
        filter_grid.addWidget(self._label("label_designation", "Designation"), row, 0)
        filter_grid.addWidget(self.des_edit, row, 1)
        filter_grid.addWidget(self._label("label_orbit_class", "Orbit class"), row, 2)
        filter_grid.addWidget(self.class_combo, row, 3, 1, 3)
        row += 1
        filter_grid.addWidget(self._label("label_h_min", "H min"), row, 0)
        filter_grid.addWidget(self.h_min_edit, row, 1)
        filter_grid.addWidget(self._label("label_h_max", "H max"), row, 2)
        filter_grid.addWidget(self.h_max_edit, row, 3)
        filter_grid.addWidget(self._label("label_vrel_minmax", "v_rel min/max"), row, 4)
        vrel_box = QHBoxLayout()
        vrel_box.addWidget(self.vrel_min_edit)
        vrel_box.addWidget(self.vrel_max_edit)
        vrel_wrap = QWidget()
        vrel_wrap.setLayout(vrel_box)
        filter_grid.addWidget(vrel_wrap, row, 5)
        row += 1
        checks = QHBoxLayout()
        for chk in [self.neo_check, self.pha_check, self.nea_check, self.comet_check, self.diameter_check, self.fullname_check]:
            checks.addWidget(chk)
        checks.addStretch(1)
        checks_wrap = QWidget()
        checks_wrap.setLayout(checks)
        filter_grid.addWidget(checks_wrap, row, 0, 1, 6)
        row += 1
        self.fetch_btn = QPushButton("Fetch NASA/JPL CAD Data")
        self.preset_earth_btn = QPushButton("Preset: next 60 days")
        self.preset_close_btn = QPushButton("Preset: < 10 LD / 365 days")
        self.preset_apophis_btn = QPushButton("Preset: Apophis 2029")
        buttons = QHBoxLayout()
        for btn in [self.fetch_btn, self.preset_earth_btn, self.preset_close_btn, self.preset_apophis_btn]:
            buttons.addWidget(btn)
        buttons.addStretch(1)
        buttons_wrap = QWidget()
        buttons_wrap.setLayout(buttons)
        filter_grid.addWidget(buttons_wrap, row, 0, 1, 6)
        layout.addWidget(filter_box)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableWidget(0, len(self.table_columns))
        self.table.setHorizontalHeaderLabels(self._translated_table_headers())
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        splitter.addWidget(self.table)
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        splitter.addWidget(self.detail_text)
        splitter.setSizes([560, 230])
        layout.addWidget(splitter, 1)

    def _build_analysis_tab(self) -> None:
        layout = QVBoxLayout(self.analysis_tab)
        box = self._group("group_ollama_analysis", "Local Ollama analysis")
        form = QFormLayout(box)
        self.ollama_url_edit = QLineEdit("http://localhost:11434")
        self.ollama_model_combo = QComboBox()
        self.ollama_model_combo.setEditable(True)
        self.ollama_model_combo.addItem("gemma4:26b")
        self.ollama_model_combo.addItem("llama3.1:8b")
        self.ollama_model_combo.addItem("qwen2.5:14b")
        model_row = QHBoxLayout()
        model_row.addWidget(self.ollama_model_combo, 1)
        self.list_models_btn = QPushButton("List models")
        model_row.addWidget(self.list_models_btn)
        model_wrap = QWidget()
        model_wrap.setLayout(model_row)
        self.num_ctx_spin = QSpinBox()
        self.num_ctx_spin.setRange(2048, 262144)
        self.num_ctx_spin.setValue(8192)
        self.num_ctx_spin.setSingleStep(2048)
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 1.5)
        self.temperature_spin.setValue(0.2)
        self.temperature_spin.setSingleStep(0.05)
        self.ollama_timeout_spin = QSpinBox()
        self.ollama_timeout_spin.setRange(30, 3600)
        self.ollama_timeout_spin.setValue(600)
        self.ollama_timeout_spin.setSingleStep(30)
        self.ollama_timeout_spin.setSuffix(" s")
        form.addRow(self._label("label_ollama_url", "Ollama URL"), self.ollama_url_edit)
        form.addRow(self._label("label_model", "Model"), model_wrap)
        form.addRow(self._label("label_context_tokens", "Context tokens"), self.num_ctx_spin)
        form.addRow(self._label("label_temperature", "Temperature"), self.temperature_spin)
        form.addRow(self._label("label_ollama_timeout", "Ollama timeout"), self.ollama_timeout_spin)
        layout.addWidget(box)

        btn_row = QHBoxLayout()
        self.analyze_selected_btn = QPushButton("Analyze selected record with Ollama")
        self.local_summary_btn = QPushButton("Local heuristic summary")
        self.cancel_ollama_btn = QPushButton("Ignore running Ollama result")
        self.cancel_ollama_btn.setVisible(False)
        self.cancel_ollama_btn.setEnabled(False)
        btn_row.addWidget(self.analyze_selected_btn)
        btn_row.addWidget(self.local_summary_btn)
        btn_row.addWidget(self.cancel_ollama_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.ollama_busy_label = QLabel("Ollama request running...")
        self.ollama_busy_label.setVisible(False)
        layout.addWidget(self.ollama_busy_label)
        self.ollama_progress = QProgressBar()
        self.ollama_progress.setRange(0, 0)
        self.ollama_progress.setVisible(False)
        layout.addWidget(self.ollama_progress)

        self.analysis_text = QTextBrowser()
        self.analysis_text.setOpenExternalLinks(True)
        self.analysis_text.setReadOnly(True)
        layout.addWidget(self.analysis_text, 1)

        follow_row = QHBoxLayout()
        self.followup_edit = QLineEdit()
        self.followup_edit.setPlaceholderText("Ask a follow-up based on the analysis...")
        self.followup_btn = QPushButton("Send follow-up")
        follow_row.addWidget(self.followup_edit, 1)
        follow_row.addWidget(self.followup_btn)
        layout.addLayout(follow_row)

        output_row = QHBoxLayout()
        self.read_analysis_btn = QPushButton("Read aloud")
        self.stop_tts_btn = QPushButton("Stop speech")
        self.stop_tts_btn.setEnabled(False)
        self.print_analysis_btn = QPushButton("Print analysis")
        self.copy_analysis_btn = QPushButton("Copy text")
        output_row.addStretch(1)
        output_row.addWidget(self.read_analysis_btn)
        output_row.addWidget(self.stop_tts_btn)
        output_row.addWidget(self.copy_analysis_btn)
        output_row.addWidget(self.print_analysis_btn)
        layout.addLayout(output_row)

    def _build_sim_tab(self) -> None:
        layout = QVBoxLayout(self.sim_tab)
        sim_box = self._group("group_simulation", "3D visualization and simplified gravitational what-if")
        form = QFormLayout(sim_box)
        self.days_before_spin = QDoubleSpinBox()
        self.days_before_spin.setRange(0.1, 365.0)
        self.days_before_spin.setValue(7.0)
        self.days_before_spin.setSuffix(" days")
        self.days_after_spin = QDoubleSpinBox()
        self.days_after_spin.setRange(0.1, 365.0)
        self.days_after_spin.setValue(7.0)
        self.days_after_spin.setSuffix(" days")
        self.step_minutes_spin = QDoubleSpinBox()
        self.step_minutes_spin.setRange(1.0, 1440.0)
        self.step_minutes_spin.setValue(60.0)
        self.step_minutes_spin.setSuffix(" min")
        self.include_sun_check = QCheckBox("Include solar tide")
        self.include_sun_check.setChecked(True)
        self.include_planets_check = QCheckBox("Include approximate major-planet tidal terms")
        self.include_planets_check.setChecked(True)
        self.target_scale_spin = QDoubleSpinBox()
        self.target_scale_spin.setRange(1.0, 1000.0)
        self.target_scale_spin.setValue(20.0)
        self.target_scale_spin.setSuffix("x visual radius")
        form.addRow(self._label("label_days_before", "Days before CA"), self.days_before_spin)
        form.addRow(self._label("label_days_after", "Days after CA"), self.days_after_spin)
        form.addRow(self._label("label_integrator_step", "Integrator step"), self.step_minutes_spin)
        form.addRow(self._label("label_solar_tide", "Solar tide"), self.include_sun_check)
        form.addRow(self._label("label_planets", "Planets"), self.include_planets_check)
        form.addRow(self._label("label_target_scale", "Target body visual scale"), self.target_scale_spin)
        layout.addWidget(sim_box)

        btn_row = QHBoxLayout()
        self.open_3d_btn = QPushButton("Open local 3D visualization")
        self.save_3d_btn = QPushButton("Create HTML only")
        btn_row.addWidget(self.open_3d_btn)
        btn_row.addWidget(self.save_3d_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.sim_text = QTextEdit()
        self.sim_text.setReadOnly(True)
        self.sim_default_active = True
        self.sim_text.setText(self._default_sim_text())
        layout.addWidget(self.sim_text, 1)

    def _build_options_tab(self) -> None:
        layout = QVBoxLayout(self.options_tab)
        box = self._group("group_options", "Application options")
        form = QFormLayout(box)
        self.language_combo = QComboBox()
        for lang in self.translator.available_languages():
            self.language_combo.addItem(lang.upper(), lang)
        initial_lang_idx = self.language_combo.findData(self.translator.language)
        if initial_lang_idx >= 0:
            self.language_combo.setCurrentIndex(initial_lang_idx)
        self.theme_combo = QComboBox()
        for theme_id, name in self.theme_manager.names():
            self.theme_combo.addItem(name, theme_id)
        self.output_path_edit = QLineEdit(str(self.output_dir))
        out_row = QHBoxLayout()
        out_row.addWidget(self.output_path_edit, 1)
        self.output_browse_btn = QPushButton("Browse")
        out_row.addWidget(self.output_browse_btn)
        out_wrap = QWidget()
        out_wrap.setLayout(out_row)
        form.addRow(self._label("label_language", "Language"), self.language_combo)
        form.addRow(self._label("label_theme", "Theme"), self.theme_combo)
        form.addRow(self._label("label_visualization_output", "Visualization output"), out_wrap)
        layout.addWidget(box)
        self.save_options_btn = QPushButton("Save options")
        layout.addWidget(self.save_options_btn)
        layout.addStretch(1)

    def _build_about_tab(self) -> None:
        layout = QVBoxLayout(self.about_tab)
        self.about_text = QTextEdit()
        self.about_text.setReadOnly(True)
        self.about_text.setHtml(self._about_html())
        layout.addWidget(self.about_text)

    def _connect_signals(self) -> None:
        self.fetch_btn.clicked.connect(self.fetch_data)
        self.preset_earth_btn.clicked.connect(self.preset_earth)
        self.preset_close_btn.clicked.connect(self.preset_close)
        self.preset_apophis_btn.clicked.connect(self.preset_apophis)
        self.table.itemSelectionChanged.connect(self.update_detail_from_selection)
        self.list_models_btn.clicked.connect(self.list_ollama_models)
        self.analyze_selected_btn.clicked.connect(self.analyze_selected)
        self.local_summary_btn.clicked.connect(self.local_summary)
        self.cancel_ollama_btn.clicked.connect(self.cancel_ollama_display)
        self.followup_btn.clicked.connect(self.ask_ollama_followup)
        self.followup_edit.returnPressed.connect(self.ask_ollama_followup)
        self.print_analysis_btn.clicked.connect(self.print_analysis)
        self.copy_analysis_btn.clicked.connect(self.copy_analysis_text)
        self.read_analysis_btn.clicked.connect(self.read_analysis_aloud)
        self.stop_tts_btn.clicked.connect(self.stop_tts)
        self.open_3d_btn.clicked.connect(lambda: self.create_visualization(open_after=True))
        self.save_3d_btn.clicked.connect(lambda: self.create_visualization(open_after=False))
        self.theme_combo.currentIndexChanged.connect(self.apply_selected_theme)
        self.language_combo.currentIndexChanged.connect(self.change_language)
        self.output_browse_btn.clicked.connect(self.browse_output_dir)
        self.save_options_btn.clicked.connect(self._save_config)
        self.open_output_btn.clicked.connect(self.open_output_folder)

    def _apply_texts(self) -> None:
        t = self.translator.t
        self.tabs.setTabText(0, t("tab_data"))
        self.tabs.setTabText(1, t("tab_analysis"))
        self.tabs.setTabText(2, t("tab_simulation"))
        self.tabs.setTabText(3, t("tab_options"))
        self.tabs.setTabText(4, t("tab_about"))

        for key, label in self.i18n_labels.items():
            label.setText(t(key))
        for key, group in self.i18n_groups.items():
            group.setTitle(t(key))

        self.fetch_btn.setText(t("fetch_data"))
        self.preset_earth_btn.setText(t("preset_next_60"))
        self.preset_close_btn.setText(t("preset_close_365"))
        self.preset_apophis_btn.setText(t("preset_apophis_2029"))
        self.analyze_selected_btn.setText(t("analyze_selected"))
        self.local_summary_btn.setText(t("local_summary"))
        self.cancel_ollama_btn.setText(t("cancel_ollama_display"))
        self.ollama_busy_label.setText(t("ollama_running"))
        self.list_models_btn.setText(t("list_models"))
        self.open_3d_btn.setText(t("open_3d"))
        self.save_3d_btn.setText(t("save_3d"))
        self.open_output_btn.setText(t("open_output"))
        self.output_browse_btn.setText(t("browse"))
        self.save_options_btn.setText(t("save_options"))
        self.followup_btn.setText(t("send_followup"))
        self.followup_edit.setPlaceholderText(t("followup_placeholder"))
        self.print_analysis_btn.setText(t("print_analysis"))
        self.copy_analysis_btn.setText(t("copy_analysis_text"))
        self.read_analysis_btn.setText(t("read_analysis_aloud"))
        self.stop_tts_btn.setText(t("stop_tts"))

        self._apply_tooltips()

        self.neo_check.setText(t("neo_filter"))
        self.pha_check.setText(t("pha_only"))
        self.nea_check.setText(t("nea_only"))
        self.comet_check.setText(t("comets_only"))
        self.diameter_check.setText(t("include_diameter"))
        self.fullname_check.setText(t("include_fullname"))
        self.include_sun_check.setText(t("include_solar_tide"))
        self.include_planets_check.setText(t("include_planet_terms"))

        self.days_before_spin.setSuffix(" " + t("unit_days"))
        self.days_after_spin.setSuffix(" " + t("unit_days"))
        self.step_minutes_spin.setSuffix(" " + t("unit_minutes"))
        self.target_scale_spin.setSuffix(" " + t("unit_visual_radius"))

        self.class_combo.setItemText(0, t("combo_any"))
        for idx in range(self.body_combo.count()):
            code = str(self.body_combo.itemData(idx))
            self.body_combo.setItemText(idx, f"{t('body_' + code)} ({code})")

        self.table.setHorizontalHeaderLabels(self._translated_table_headers())
        self.about_text.setHtml(self._about_html())
        if self.analysis_markdown:
            self._render_analysis_markdown(self.analysis_markdown)
        if self.sim_default_active:
            self.sim_text.setText(self._default_sim_text())

    def _apply_tooltips(self) -> None:
        t = self.translator.t
        tooltip_map = {
            self.fetch_btn: "tip_fetch_data",
            self.preset_earth_btn: "tip_preset_next_60",
            self.preset_close_btn: "tip_preset_close_365",
            self.preset_apophis_btn: "tip_preset_apophis",
            self.neo_check: "tip_neo_filter",
            self.pha_check: "tip_pha_only",
            self.nea_check: "tip_nea_only",
            self.comet_check: "tip_comets_only",
            self.diameter_check: "tip_include_diameter",
            self.fullname_check: "tip_include_fullname",
            self.list_models_btn: "tip_list_models",
            self.analyze_selected_btn: "tip_analyze_selected",
            self.local_summary_btn: "tip_local_summary",
            self.cancel_ollama_btn: "tip_cancel_ollama",
            self.followup_edit: "tip_followup_prompt",
            self.followup_btn: "tip_send_followup",
            self.print_analysis_btn: "tip_print_analysis",
            self.copy_analysis_btn: "tip_copy_analysis",
            self.read_analysis_btn: "tip_read_analysis",
            self.stop_tts_btn: "tip_stop_tts",
            self.open_3d_btn: "tip_open_3d",
            self.save_3d_btn: "tip_save_3d",
            self.output_browse_btn: "tip_browse_output",
            self.open_output_btn: "tip_open_output",
            self.save_options_btn: "tip_save_options",
            self.language_combo: "tip_language",
            self.theme_combo: "tip_theme",
        }
        for widget, key in tooltip_map.items():
            widget.setToolTip(t(key))

    def _inline_markdown_to_html(self, text: str) -> str:
        escaped = html.escape(text)
        code_fragments: list[str] = []

        def hold_code(match: re.Match[str]) -> str:
            code_fragments.append(f"<code>{match.group(1)}</code>")
            return f"@@CODE{len(code_fragments) - 1}@@"

        escaped = re.sub(r"`([^`]+)`", hold_code, escaped)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong><em>\1</em></strong>", escaped)
        escaped = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", escaped)
        for idx, fragment in enumerate(code_fragments):
            escaped = escaped.replace(f"@@CODE{idx}@@", fragment)
        return escaped

    def _rich_markdown_html(self, markdown_text: str) -> str:
        text_color = self.palette().text().color().name()
        link_color = self.palette().highlight().color().name()
        lines = markdown_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        body: list[str] = []
        in_code = False
        code_lines: list[str] = []
        for raw in lines:
            line = raw.rstrip()
            stripped = line.strip()
            if stripped.startswith("```"):
                if in_code:
                    body.append("<pre>" + html.escape("\n".join(code_lines)) + "</pre>")
                    code_lines = []
                    in_code = False
                else:
                    in_code = True
                    code_lines = []
                continue
            if in_code:
                code_lines.append(line)
                continue
            if not stripped:
                body.append("<div class='space'></div>")
                continue
            heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if heading:
                level = min(len(heading.group(1)), 4)
                body.append(f"<h{level}>{self._inline_markdown_to_html(heading.group(2))}</h{level}>")
                continue
            if re.fullmatch(r"[-*_]{3,}", stripped):
                body.append("<hr>")
                continue
            bullet = re.match(r"^\s*[*\-]\s+(.*)$", line)
            if bullet:
                body.append("<div class='bullet'><span class='arrow'>➜</span><span>" + self._inline_markdown_to_html(bullet.group(1)) + "</span></div>")
                continue
            numbered = re.match(r"^\s*(\d+)\.\s+(.*)$", line)
            if numbered:
                body.append("<div class='numbered'><span class='num'>" + html.escape(numbered.group(1)) + "</span><span>" + self._inline_markdown_to_html(numbered.group(2)) + "</span></div>")
                continue
            body.append("<p>" + self._inline_markdown_to_html(stripped) + "</p>")
        if in_code:
            body.append("<pre>" + html.escape("\n".join(code_lines)) + "</pre>")
        css = f"""
        <style>
        body {{ font-family: Segoe UI, Arial, sans-serif; font-size: 10.5pt; color: {text_color}; }}
        h1 {{ font-size: 21pt; margin: 14px 0 8px 0; }}
        h2 {{ font-size: 17pt; margin: 12px 0 7px 0; }}
        h3 {{ font-size: 14pt; margin: 11px 0 6px 0; }}
        h4 {{ font-size: 12pt; margin: 10px 0 5px 0; }}
        p {{ margin: 4px 0 6px 0; line-height: 1.32; }}
        .space {{ height: 8px; }}
        .bullet {{ margin: 4px 0 4px 18px; line-height: 1.32; }}
        .arrow {{ color: {link_color}; font-weight: 700; margin-right: 8px; }}
        .numbered {{ margin: 4px 0 4px 18px; line-height: 1.32; }}
        .num {{ display: inline-block; min-width: 20px; color: {link_color}; font-weight: 700; }}
        strong {{ font-weight: 700; }}
        em {{ font-style: italic; }}
        code {{ font-family: Consolas, monospace; padding: 1px 4px; }}
        pre {{ font-family: Consolas, monospace; white-space: pre-wrap; padding: 8px; border: 1px solid {link_color}; }}
        hr {{ border: 0; border-top: 1px solid {link_color}; margin: 10px 0; }}
        </style>
        """
        return "<html><head>" + css + "</head><body>" + "\n".join(body) + "</body></html>"

    def _render_analysis_markdown(self, markdown_text: str) -> None:
        self.analysis_text.setHtml(self._rich_markdown_html(markdown_text))

    def _set_analysis_markdown(self, markdown_text: str, *, clear_chat: bool = False) -> None:
        self.analysis_markdown = markdown_text.strip()
        if clear_chat:
            self.chat_turns.clear()
        self._render_analysis_markdown(self.analysis_markdown)

    def _append_chat_turn(self, user_text: str, assistant_text: str) -> None:
        self.chat_turns.append((user_text.strip(), assistant_text.strip()))
        parts = [self.analysis_markdown.strip()]
        for idx, (question, answer) in enumerate(self.chat_turns, 1):
            parts.append(f"\n---\n\n### {self.translator.t('followup_turn_heading')} {idx}\n\n**{self.translator.t('followup_user_label')}:** {question}\n\n**{self.translator.t('followup_ollama_label')}:**\n\n{answer}")
        self._render_analysis_markdown("\n".join(parts))

    def _selected_record_context(self) -> str:
        record = self.selected_record()
        if not record:
            return self.translator.t("followup_no_record_context")
        return "\n".join(record.summary_lines())

    def _current_response_language_name(self) -> str:
        lang = str(self.language_combo.currentData() or self.translator.language or "en")
        return {
            "en": "English",
            "de": "German",
            "fr": "French",
            "ru": "Russian",
        }.get(lang, "English")

    def _current_tts_culture(self) -> str:
        lang = str(self.language_combo.currentData() or self.translator.language or "en")
        return {
            "en": "en-US",
            "de": "de-DE",
            "fr": "fr-FR",
            "ru": "ru-RU",
        }.get(lang, "en-US")

    def read_analysis_aloud(self) -> None:
        text = self.analysis_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, self.translator.t("tts_no_text_title"), self.translator.t("tts_no_text"))
            return
        if os.name != "nt":
            QMessageBox.information(self, self.translator.t("tts_unavailable_title"), self.translator.t("tts_windows_only"))
            return
        self.stop_tts()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix="jpl_cad_tts_", suffix=".txt")
        os.close(fd)
        self.tts_temp_file = Path(temp_name)
        self.tts_temp_file.write_text(text, encoding="utf-8")
        culture = self._current_tts_culture()
        ps = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$culture = New-Object System.Globalization.CultureInfo('" + culture + "'); "
            "try { $s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::NotSet, [System.Speech.Synthesis.VoiceAge]::NotSet, 0, $culture) } catch { }; "
            "$txt = Get-Content -Raw -Encoding UTF8 -LiteralPath '" + str(self.tts_temp_file).replace("'", "''") + "'; "
            "$s.Speak($txt);"
        )
        try:
            self.tts_process = subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            self.tts_process = None
            self._cleanup_tts_temp_file()
            QMessageBox.warning(self, self.translator.t("tts_error_title"), f"{self.translator.t('tts_start_failed')}\n\n{exc}")
            return
        self.read_analysis_btn.setEnabled(False)
        self.stop_tts_btn.setEnabled(True)
        self.tts_poll_timer.start()
        self._set_status(self.translator.t("status_tts_running"))

    def _poll_tts_process(self) -> None:
        if self.tts_process is None:
            self.tts_poll_timer.stop()
            return
        if self.tts_process.poll() is None:
            return
        self.tts_process = None
        self.tts_poll_timer.stop()
        self.read_analysis_btn.setEnabled(True)
        self.stop_tts_btn.setEnabled(False)
        self._cleanup_tts_temp_file()
        self._set_status(self.translator.t("status_tts_finished"))

    def stop_tts(self) -> None:
        if self.tts_process is not None and self.tts_process.poll() is None:
            try:
                self.tts_process.terminate()
            except Exception:
                pass
            self._set_status(self.translator.t("status_tts_stopped"))
        self.tts_process = None
        self.tts_poll_timer.stop()
        if hasattr(self, "read_analysis_btn"):
            self.read_analysis_btn.setEnabled(True)
        if hasattr(self, "stop_tts_btn"):
            self.stop_tts_btn.setEnabled(False)
        self._cleanup_tts_temp_file()

    def _cleanup_tts_temp_file(self) -> None:
        if self.tts_temp_file is not None:
            try:
                self.tts_temp_file.unlink(missing_ok=True)
            except Exception:
                pass
            self.tts_temp_file = None

    def print_analysis(self) -> None:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle(self.translator.t("print_analysis"))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.analysis_text.document().print(printer)

    def copy_analysis_text(self) -> None:
        QApplication.clipboard().setText(self.analysis_text.toPlainText())
        self._set_status(self.translator.t("status_analysis_copied"))

    def _load_config(self) -> None:
        if not self.config_path.exists():
            lang_idx = self.language_combo.findData(self.translator.language)
            if lang_idx >= 0:
                self.language_combo.setCurrentIndex(lang_idx)
            self.apply_selected_theme()
            return
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            self.ollama_url_edit.setText(data.get("ollama_url", self.ollama_url_edit.text()))
            model = data.get("ollama_model")
            if model:
                self.ollama_model_combo.setCurrentText(model)
            try:
                self.ollama_timeout_spin.setValue(int(data.get("ollama_timeout_seconds", self.ollama_timeout_spin.value())))
            except Exception:
                pass
            self.output_path_edit.setText(data.get("output_dir", self.output_path_edit.text()))
            self.output_dir = Path(self.output_path_edit.text())
            theme_id = data.get("theme", "dark")
            idx = self.theme_combo.findData(theme_id)
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)
            lang = data.get("language", "en")
            lidx = self.language_combo.findData(lang)
            if lidx >= 0:
                self.language_combo.setCurrentIndex(lidx)
                self.translator.load(lang)
            self.apply_selected_theme()
        except Exception:
            self.apply_selected_theme()

    def _save_config(self) -> None:
        self.output_dir = Path(self.output_path_edit.text()).expanduser()
        data = {
            "ollama_url": self.ollama_url_edit.text().strip(),
            "ollama_model": self.ollama_model_combo.currentText().strip(),
            "ollama_timeout_seconds": int(self.ollama_timeout_spin.value()),
            "theme": self.theme_combo.currentData(),
            "language": self.language_combo.currentData(),
            "output_dir": str(self.output_dir),
        }
        self.config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._set_status(self.translator.t("status_options_saved"))

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def current_query(self) -> CadQuery:
        return CadQuery(
            date_min=self.date_min_edit.text().strip() or "now",
            date_max=self.date_max_edit.text().strip() or "+60",
            dist_max=self.dist_max_edit.text().strip() or "0.05",
            body=str(self.body_combo.currentData()),
            sort=self.sort_combo.currentText(),
            limit=int(self.limit_spin.value()),
            des=self.des_edit.text().strip(),
            orbit_class=str(self.class_combo.currentData() or ""),
            h_min=self.h_min_edit.text().strip(),
            h_max=self.h_max_edit.text().strip(),
            v_rel_min=self.vrel_min_edit.text().strip(),
            v_rel_max=self.vrel_max_edit.text().strip(),
            neo=self.neo_check.isChecked(),
            pha=self.pha_check.isChecked(),
            nea=self.nea_check.isChecked(),
            comet=self.comet_check.isChecked(),
            diameter=self.diameter_check.isChecked(),
            fullname=self.fullname_check.isChecked(),
        )

    def fetch_data(self) -> None:
        query = self.current_query()
        self._set_status(f"Fetching JPL CAD data: {query.url()}")
        self.fetch_btn.setEnabled(False)

        def job() -> tuple[dict, list[CadRecord], str]:
            payload = CadApiClient().fetch(query)
            records = parse_cad_payload(payload, query_body=query.body)
            return payload, records, query.url()

        worker: Worker = Worker(job)
        self.current_worker = worker
        worker.finished_ok.connect(self._fetch_done)
        worker.failed.connect(self._worker_failed)
        worker.finished.connect(lambda: self.fetch_btn.setEnabled(True))
        worker.start()

    def _fetch_done(self, result: object) -> None:
        payload, records, url = result  # type: ignore[misc]
        self.records = records
        self.populate_table(records)
        version = (payload.get("signature") or {}).get("version", "unknown")
        count = payload.get("count", len(records))
        total = payload.get("total")
        total_text = f" / total {total}" if total is not None else ""
        self._set_status(f"Loaded {count}{total_text} CAD records. API version: {version}. URL: {url}")
        if not records:
            self.detail_text.setText("No matching records. Try a wider date range or distance filter.")

    def _worker_failed(self, message: str) -> None:
        self._set_status(self.translator.t("status_operation_failed"))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = self.log_dir / f"error_{stamp}.txt"
        try:
            log_path.write_text(message, encoding="utf-8")
        except Exception:
            log_path = None  # type: ignore[assignment]
        first_line = (message.strip().splitlines() or [self.translator.t("error_unknown")])[0]
        dlg = ErrorDetailsDialog(
            self,
            self.translator.t("error_title"),
            first_line,
            message,
            log_path,
            self.translator.t("error_copy_details"),
            self.translator.t("error_save_as"),
            self.translator.t("ok"),
            self.translator.t("error_save_details"),
        )
        dlg.exec()

    def populate_table(self, records: list[CadRecord]) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(records))
        for row_idx, record in enumerate(records):
            values = record.table_values()
            numeric_map = {
                "Distance LD": record.distance_ld,
                "Min LD": record.min_distance_ld,
                "Max LD": record.max_distance_ld,
                "Distance km": record.distance_km,
                "v_rel km/s": record.v_rel_kms,
                "H": record.h_mag,
            }
            for col_idx, col in enumerate(self.table_columns):
                text = values.get(col, "")
                item = NumericItem(text, numeric_map.get(col))
                if col in numeric_map:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row_idx, col_idx, item)
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)
        if records:
            self.table.selectRow(0)
            self.update_detail_from_selection()

    def selected_record(self) -> CadRecord | None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        # Sorting changes visual row order, so map by visible object + date rather than row index.
        row = rows[0].row()
        object_item = self.table.item(row, 0)
        date_item = self.table.item(row, 1)
        object_text = object_item.text() if object_item else ""
        date_text = date_item.text() if date_item else ""
        for rec in self.records:
            values = rec.table_values()
            if values.get("Object") == object_text and values.get("Date TDB") == date_text:
                return rec
        if 0 <= row < len(self.records):
            return self.records[row]
        return None

    def update_detail_from_selection(self) -> None:
        record = self.selected_record()
        if not record:
            return
        self.detail_text.setText("\n".join(record.summary_lines()))

    def preset_earth(self) -> None:
        self.date_min_edit.setText("now")
        self.date_max_edit.setText("+60")
        self.dist_max_edit.setText("0.05")
        self.body_combo.setCurrentIndex(self.body_combo.findData("Earth"))
        self.limit_spin.setValue(100)
        self.des_edit.clear()
        self.sort_combo.setCurrentText("date")

    def preset_close(self) -> None:
        self.date_min_edit.setText("now")
        self.date_max_edit.setText("+365")
        self.dist_max_edit.setText("10LD")
        self.body_combo.setCurrentIndex(self.body_combo.findData("Earth"))
        self.limit_spin.setValue(250)
        self.des_edit.clear()
        self.sort_combo.setCurrentText("dist")

    def preset_apophis(self) -> None:
        self.date_min_edit.setText("2029-01-01")
        self.date_max_edit.setText("2029-12-31")
        self.dist_max_edit.setText("0.1")
        self.body_combo.setCurrentIndex(self.body_combo.findData("Earth"))
        self.limit_spin.setValue(20)
        self.des_edit.setText("99942")
        self.class_combo.setCurrentIndex(0)
        self.h_min_edit.clear()
        self.h_max_edit.clear()
        self.vrel_min_edit.clear()
        self.vrel_max_edit.clear()
        self.neo_check.setChecked(False)
        self.pha_check.setChecked(False)
        self.nea_check.setChecked(False)
        self.comet_check.setChecked(False)
        self.sort_combo.setCurrentText("date")

    def list_ollama_models(self) -> None:
        self._set_status("Listing Ollama models...")
        self.list_models_btn.setEnabled(False)

        def job() -> list[str]:
            return OllamaClient(self.ollama_url_edit.text().strip()).list_models()

        worker: Worker = Worker(job)
        self.current_worker = worker
        worker.finished_ok.connect(self._models_done)
        worker.failed.connect(self._worker_failed)
        worker.finished.connect(lambda: self.list_models_btn.setEnabled(True))
        worker.start()

    def _models_done(self, models: object) -> None:
        models = list(models)  # type: ignore[arg-type]
        current = self.ollama_model_combo.currentText()
        self.ollama_model_combo.clear()
        for model in models:
            self.ollama_model_combo.addItem(str(model))
        if current:
            self.ollama_model_combo.setCurrentText(current)
        self._set_status(f"Found {len(models)} Ollama models.")

    def _format_ollama_elapsed(self) -> str:
        elapsed = max(0, int(time.monotonic() - self.ollama_started_at)) if self.ollama_started_at else 0
        timeout_seconds = int(self.ollama_timeout_spin.value())
        base = self.ollama_busy_base_message or self.translator.t("ollama_running")
        return f"{base}  {self.translator.t('ollama_elapsed')}: {elapsed} s / {self.translator.t('ollama_timeout_short')}: {timeout_seconds} s"

    def _update_ollama_elapsed_label(self) -> None:
        if self.active_ollama_request_id is None:
            self.ollama_elapsed_timer.stop()
            return
        self.ollama_busy_label.setText(self._format_ollama_elapsed())

    def _set_ollama_busy(self, busy: bool, message: str | None = None) -> None:
        self.ollama_progress.setVisible(busy)
        self.ollama_busy_label.setVisible(busy or bool(message))
        self.cancel_ollama_btn.setVisible(busy)
        self.cancel_ollama_btn.setEnabled(busy)
        if busy:
            self.ollama_busy_base_message = message or self.translator.t("ollama_running")
            if not self.ollama_elapsed_timer.isActive():
                self.ollama_started_at = time.monotonic()
                self.ollama_elapsed_timer.start()
            self.ollama_busy_label.setText(self._format_ollama_elapsed())
        else:
            self.ollama_elapsed_timer.stop()
            self.ollama_started_at = 0.0
            if message is not None:
                self.ollama_busy_base_message = message
                self.ollama_busy_label.setText(message)
            else:
                self.ollama_busy_base_message = ""


    def analyze_selected(self) -> None:
        record = self.selected_record()
        if not record:
            QMessageBox.information(self, "No selection", "Select a CAD record first.")
            return
        self.tabs.setCurrentWidget(self.analysis_tab)
        self.analysis_request_id += 1
        request_id = self.analysis_request_id
        self.active_ollama_request_id = request_id
        prompt = build_ollama_prompt(record, response_language=self._current_response_language_name())
        model = self.ollama_model_combo.currentText().strip()
        timeout_seconds = int(self.ollama_timeout_spin.value())
        self._set_analysis_markdown(
            f"### {self.translator.t('ollama_sending')}\n\n"
            f"**Model:** {model}\n\n"
            f"**Timeout:** {timeout_seconds} s\n\n"
            "---\n\n"
            + prompt,
            clear_chat=True,
        )
        self.analyze_selected_btn.setEnabled(False)
        self._set_ollama_busy(True, self.translator.t("ollama_running"))
        self._set_status(self.translator.t("status_ollama_running"))

        def job() -> str:
            client = OllamaClient(self.ollama_url_edit.text().strip(), timeout_seconds=timeout_seconds)
            return client.generate(
                model,
                prompt,
                temperature=float(self.temperature_spin.value()),
                num_ctx=int(self.num_ctx_spin.value()),
            )

        worker: Worker = Worker(job)
        self.current_worker = worker
        worker.finished_ok.connect(lambda text, rid=request_id: self._ollama_done(rid, str(text)))
        worker.failed.connect(lambda message, rid=request_id: self._ollama_failed(rid, str(message)))
        worker.finished.connect(lambda rid=request_id: self._ollama_finished(rid))
        worker.start()

    def _ollama_done(self, request_id: int, text: str) -> None:
        if self.active_ollama_request_id != request_id:
            return
        self._set_analysis_markdown(text or self.translator.t("ollama_empty_response"), clear_chat=True)
        self._set_status(self.translator.t("status_ollama_complete"))

    def _ollama_failed(self, request_id: int, message: str) -> None:
        if self.active_ollama_request_id != request_id:
            self._set_status(self.translator.t("status_ollama_ignored"))
            return
        self._worker_failed(message)

    def _ollama_finished(self, request_id: int) -> None:
        if self.active_ollama_request_id == request_id:
            self.active_ollama_request_id = None
            self._set_ollama_busy(False)
        self.analyze_selected_btn.setEnabled(True)
        self.followup_btn.setEnabled(True)

    def cancel_ollama_display(self) -> None:
        if self.active_ollama_request_id is None:
            return
        self.active_ollama_request_id = None
        self._set_ollama_busy(False, self.translator.t("ollama_ignored_notice"))
        self._set_status(self.translator.t("status_ollama_ignored"))
        self.analyze_selected_btn.setEnabled(True)
        self.followup_btn.setEnabled(True)

    def local_summary(self) -> None:
        record = self.selected_record()
        if not record:
            QMessageBox.information(self, "No selection", "Select a CAD record first.")
            return
        if self.active_ollama_request_id is not None:
            self.cancel_ollama_display()
        self.tabs.setCurrentWidget(self.analysis_tab)
        self._set_analysis_markdown(fallback_analysis(record, language=str(self.language_combo.currentData() or self.translator.language)), clear_chat=True)


    def ask_ollama_followup(self) -> None:
        question = self.followup_edit.text().strip()
        if not question:
            return
        if self.active_ollama_request_id is not None:
            QMessageBox.information(self, self.translator.t("ollama_busy_title"), self.translator.t("ollama_busy_followup"))
            return
        base_text = self.analysis_text.toPlainText().strip() or self.analysis_markdown.strip()
        if not base_text:
            QMessageBox.information(self, self.translator.t("no_analysis_title"), self.translator.t("no_analysis_for_followup"))
            return
        self.followup_edit.clear()
        self.tabs.setCurrentWidget(self.analysis_tab)
        self.analysis_request_id += 1
        request_id = self.analysis_request_id
        self.active_ollama_request_id = request_id
        model = self.ollama_model_combo.currentText().strip()
        timeout_seconds = int(self.ollama_timeout_spin.value())
        response_language = self._current_response_language_name()
        prompt = (
            "You are continuing a local scientific assistant conversation inside a NASA/JPL CAD desktop GUI.\n"
            "Answer the user's follow-up using the prior analysis and selected CAD record context.\n"
            "Stay careful: distinguish CAD summary data, local heuristics, and official impact-risk assessment.\n"
            f"Answer strictly in {response_language}.\n\n"
            "Selected CAD record context:\n"
            f"{self._selected_record_context()}\n\n"
            "Current rendered analysis/chat text:\n"
            f"{base_text[-12000:]}\n\n"
            "User follow-up question:\n"
            f"{question}\n\n"
            "Use concise Markdown headings and bullets where helpful."
        )
        preview = f"{self.analysis_markdown}\n\n---\n\n### {self.translator.t('followup_pending_heading')}\n\n**{self.translator.t('followup_user_label')}:** {question}\n\n{self.translator.t('followup_waiting')}"
        self._render_analysis_markdown(preview)
        self.analyze_selected_btn.setEnabled(False)
        self.followup_btn.setEnabled(False)
        self._set_ollama_busy(True, self.translator.t("ollama_followup_running"))
        self._set_status(self.translator.t("status_ollama_running"))

        def job() -> str:
            client = OllamaClient(self.ollama_url_edit.text().strip(), timeout_seconds=timeout_seconds)
            return client.generate(
                model,
                prompt,
                temperature=float(self.temperature_spin.value()),
                num_ctx=int(self.num_ctx_spin.value()),
            )

        worker: Worker = Worker(job)
        self.current_worker = worker
        worker.finished_ok.connect(lambda text, rid=request_id, q=question: self._ollama_followup_done(rid, q, str(text)))
        worker.failed.connect(lambda message, rid=request_id: self._ollama_failed(rid, str(message)))
        worker.finished.connect(lambda rid=request_id: self._ollama_finished(rid))
        worker.start()

    def _ollama_followup_done(self, request_id: int, question: str, text: str) -> None:
        if self.active_ollama_request_id != request_id:
            return
        self._append_chat_turn(question, text or self.translator.t("ollama_empty_response"))
        self._set_status(self.translator.t("status_ollama_complete"))
    def create_visualization(self, open_after: bool) -> None:
        record = self.selected_record()
        if not record:
            QMessageBox.information(self, "No selection", "Select a CAD record first.")
            return
        self.tabs.setCurrentWidget(self.sim_tab)
        self._save_config()
        self.open_3d_btn.setEnabled(False)
        self.save_3d_btn.setEnabled(False)
        self.sim_default_active = False
        self.sim_text.setPlainText("Creating local 3D visualization and running simplified RK4 simulation...")
        settings = SimulationSettings(
            days_before=float(self.days_before_spin.value()),
            days_after=float(self.days_after_spin.value()),
            step_minutes=float(self.step_minutes_spin.value()),
            include_sun=self.include_sun_check.isChecked(),
            include_major_planets=self.include_planets_check.isChecked(),
        )
        target_scale = float(self.target_scale_spin.value())
        output_dir = Path(self.output_path_edit.text()).expanduser()

        def job() -> tuple[str, str]:
            sim = simulate_close_approach(record, settings)
            html_path = create_visualization_html(record, sim, output_dir, target_scale=target_scale)
            summary = [
                f"Visualization: {html_path}",
                "",
                "Simulation minima:",
                f"- Straight-line geometry: {sim.min_distance_km(sim.straight):,.0f} km",
                f"- Central-body gravity only: {sim.min_distance_km(sim.two_body):,.0f} km",
            ]
            if sim.n_body is not None:
                summary.append(f"- Approx. Sun + planet tidal terms: {sim.min_distance_km(sim.n_body):,.0f} km")
            summary.extend([
                "",
                "Scientific limitation:",
                "This is a synthetic target-centered flyby generated from CAD miss distance and relative speed. It is useful for scale intuition and rough perturbation sensitivity only. It is not orbit determination.",
            ])
            return str(html_path), "\n".join(summary)

        worker: Worker = Worker(job)
        self.current_worker = worker

        def done(result: object) -> None:
            html_path, summary = result  # type: ignore[misc]
            self.sim_text.setPlainText(summary)
            self._set_status(f"Visualization created: {html_path}")
            if open_after:
                open_html(Path(html_path))

        worker.finished_ok.connect(done)
        worker.failed.connect(self._worker_failed)
        worker.finished.connect(lambda: self.open_3d_btn.setEnabled(True))
        worker.finished.connect(lambda: self.save_3d_btn.setEnabled(True))
        worker.start()

    def apply_selected_theme(self) -> None:
        theme_id = str(self.theme_combo.currentData() or "dark")
        self.theme_manager.apply(self.app, theme_id)

    def change_language(self) -> None:
        lang = str(self.language_combo.currentData() or "en")
        self.translator.load(lang)
        self._apply_texts()

    def browse_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select visualization output directory", self.output_path_edit.text())
        if selected:
            self.output_path_edit.setText(selected)
            self.output_dir = Path(selected)

    def open_output_folder(self) -> None:
        path = Path(self.output_path_edit.text()).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            open_html(path)
