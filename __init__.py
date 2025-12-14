# -*- coding: utf-8 -*-
"""
5-level difficulty tag auto-assigner
(VeryHard / Hard / Medium / Easy / VeryEasy)

- Adds a custom config GUI opened from:
  Tools → Add-ons → (this add-on) → Config
- IMPORTANT: Does NOT add any new Tools menu entry for settings.
"""

from __future__ import annotations

from typing import Dict, Any

from aqt import mw
from aqt.qt import (
    QAction,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QFormLayout,
    QSpinBox,
    QLabel,
    QPushButton,
)
from aqt.utils import tooltip, getText
from anki.collection import Collection
from aqt.operations import QueryOp


# --------------------
# Tags to be added
# --------------------
VERY_HARD_TAG = "VeryHard"
HARD_TAG = "Hard"
MEDIUM_TAG = "Medium"
EASY_TAG = "Easy"
VERY_EASY_TAG = "VeryEasy"

ALL_TAGS = [VERY_HARD_TAG, HARD_TAG, MEDIUM_TAG, EASY_TAG, VERY_EASY_TAG]


# --------------------
# Config defaults
# --------------------
DEFAULTS: Dict[str, int] = {
    "very_hard_lapses_min": 5,
    "very_hard_ease_max_pct": 200,

    "hard_lapses_min": 3,
    "hard_ease_max_pct": 230,

    "easy_lapses_max": 0,
    "easy_ivl_min": 21,
    "easy_ease_min_pct": 250,

    "very_easy_ivl_min": 90,
    "very_easy_ease_min_pct": 280,
}


def get_cfg() -> Dict[str, Any]:
    cfg = mw.addonManager.getConfig(__name__) or {}
    for k, v in DEFAULTS.items():
        cfg.setdefault(k, v)
    return cfg


def _write_config_keep_unknown(updated: Dict[str, Any]) -> None:
    """
    Keep unknown keys: start from existing config, overwrite known keys only.
    """
    base = mw.addonManager.getConfig(__name__) or {}
    for k in DEFAULTS.keys():
        if k in updated:
            base[k] = updated[k]

    # Anki recent builds
    try:
        mw.addonManager.writeConfig(__name__, base)
        return
    except Exception:
        pass

    # Fallback (older builds)
    try:
        mw.addonManager.setConfig(__name__, base)
    except Exception:
        # last resort: ignore
        pass


# =====================================
# 5-level difficulty logic
# =====================================
def judge_difficulty(c, cfg: Dict[str, Any]) -> str:
    lapses = c.lapses
    ivl = c.ivl
    ease = c.factor  # Anki uses factor = ease% * 10 (e.g. 250% -> 2500)

    # Read config (percentage → factor)
    vh_lapses = int(cfg["very_hard_lapses_min"])
    vh_ease_max = int(cfg["very_hard_ease_max_pct"]) * 10

    h_lapses = int(cfg["hard_lapses_min"])
    h_ease_max = int(cfg["hard_ease_max_pct"]) * 10

    e_lapses_max = int(cfg["easy_lapses_max"])
    e_ivl_min = int(cfg["easy_ivl_min"])
    e_ease_min = int(cfg["easy_ease_min_pct"]) * 10

    ve_ivl_min = int(cfg["very_easy_ivl_min"])
    ve_ease_min = int(cfg["very_easy_ease_min_pct"]) * 10

    # --- decision order ---
    # Very Hard
    if lapses >= vh_lapses or ease < vh_ease_max:
        return VERY_HARD_TAG

    # Hard
    if lapses >= h_lapses or ease < h_ease_max:
        return HARD_TAG

    # Very Easy
    if ivl >= ve_ivl_min or ease >= ve_ease_min:
        return VERY_EASY_TAG

    # Easy
    if (lapses <= e_lapses_max) and (ivl >= e_ivl_min) and (ease >= e_ease_min):
        return EASY_TAG

    # Medium (default)
    return MEDIUM_TAG


# =====================================
# Background operations
# =====================================
def _assign_difficulty_tags(col: Collection, search: str, cfg: dict) -> int:
    if search.strip():
        cid_list = col.find_cards(search)
    else:
        cid_list = col.db.list("SELECT id FROM cards")

    if not cid_list:
        return 0

    note_stats: Dict[int, str] = {}

    # 1. Judge difficulty per card
    for cid in cid_list:
        c = col.get_card(cid)
        if c.reps == 0:
            continue

        nid = c.nid
        tag = judge_difficulty(c, cfg)
        note_stats[nid] = tag

    # 2. Apply tags per note
    processed = 0
    for nid, tag in note_stats.items():
        note = col.get_note(nid)

        changed = False
        # Remove existing difficulty tags
        for t in ALL_TAGS:
            if t in note.tags:
                note.tags.remove(t)
                changed = True

        # Add new tag
        note.tags.append(tag)
        changed = True

        if changed:
            col.update_note(note)
            processed += 1

    return processed



# =====================================
# Custom config GUI (opened from Add-ons → Config)
# =====================================
class ConfigDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Difficulty Tag Auto-Assigner — Settings")
        self.setMinimumWidth(640)

        cfg = get_cfg()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # --- helper ---
        def mk_spin(minv: int, maxv: int, step: int, value: int, suffix: str = "") -> QSpinBox:
            s = QSpinBox()
            s.setRange(minv, maxv)
            s.setSingleStep(step)
            s.setValue(int(value))
            if suffix:
                s.setSuffix(suffix)
            return s

        hint = QLabel(
            "Rules are evaluated in this order: VeryHard → Hard → VeryEasy → Easy → Medium.\n"
            "Ease thresholds are in percent (e.g., 250 = 250%)."
        )
        hint.setWordWrap(True)
        root.addWidget(hint)

        # --- Very Hard ---
        box_vh = QGroupBox("Very Hard")
        form_vh = QFormLayout(box_vh)
        form_vh.setVerticalSpacing(10)
        self.vh_lapses = mk_spin(0, 999, 1, cfg["very_hard_lapses_min"])
        self.vh_ease_max = mk_spin(0, 500, 5, cfg["very_hard_ease_max_pct"], "%")
        form_vh.addRow("Minimum lapses (≥)", self.vh_lapses)
        form_vh.addRow("Max ease (<)", self.vh_ease_max)
        root.addWidget(box_vh)

        # --- Hard ---
        box_h = QGroupBox("Hard")
        form_h = QFormLayout(box_h)
        form_h.setVerticalSpacing(10)
        self.h_lapses = mk_spin(0, 999, 1, cfg["hard_lapses_min"])
        self.h_ease_max = mk_spin(0, 500, 5, cfg["hard_ease_max_pct"], "%")
        form_h.addRow("Minimum lapses (≥)", self.h_lapses)
        form_h.addRow("Max ease (<)", self.h_ease_max)
        root.addWidget(box_h)

        # --- Easy ---
        box_e = QGroupBox("Easy")
        form_e = QFormLayout(box_e)
        form_e.setVerticalSpacing(10)
        self.e_lapses_max = mk_spin(0, 999, 1, cfg["easy_lapses_max"])
        self.e_ivl_min = mk_spin(0, 9999, 1, cfg["easy_ivl_min"], " days")
        self.e_ease_min = mk_spin(0, 500, 5, cfg["easy_ease_min_pct"], "%")
        form_e.addRow("Max lapses (≤)", self.e_lapses_max)
        form_e.addRow("Min interval (≥)", self.e_ivl_min)
        form_e.addRow("Min ease (≥)", self.e_ease_min)
        root.addWidget(box_e)

        # --- Very Easy ---
        box_ve = QGroupBox("Very Easy")
        form_ve = QFormLayout(box_ve)
        form_ve.setVerticalSpacing(10)
        self.ve_ivl_min = mk_spin(0, 9999, 1, cfg["very_easy_ivl_min"], " days")
        self.ve_ease_min = mk_spin(0, 500, 5, cfg["very_easy_ease_min_pct"], "%")
        form_ve.addRow("Min interval (≥)", self.ve_ivl_min)
        form_ve.addRow("Min ease (≥)", self.ve_ease_min)
        root.addWidget(box_ve)

        # --- buttons ---
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_reset = QPushButton("Reset to defaults")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Save")

        self.btn_reset.clicked.connect(self._reset_defaults)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._save)

        btn_row.addWidget(self.btn_reset)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)

        root.addLayout(btn_row)

    def _reset_defaults(self) -> None:
        self.vh_lapses.setValue(DEFAULTS["very_hard_lapses_min"])
        self.vh_ease_max.setValue(DEFAULTS["very_hard_ease_max_pct"])

        self.h_lapses.setValue(DEFAULTS["hard_lapses_min"])
        self.h_ease_max.setValue(DEFAULTS["hard_ease_max_pct"])

        self.e_lapses_max.setValue(DEFAULTS["easy_lapses_max"])
        self.e_ivl_min.setValue(DEFAULTS["easy_ivl_min"])
        self.e_ease_min.setValue(DEFAULTS["easy_ease_min_pct"])

        self.ve_ivl_min.setValue(DEFAULTS["very_easy_ivl_min"])
        self.ve_ease_min.setValue(DEFAULTS["very_easy_ease_min_pct"])

    def _save(self) -> None:
        updated = {
            "very_hard_lapses_min": int(self.vh_lapses.value()),
            "very_hard_ease_max_pct": int(self.vh_ease_max.value()),

            "hard_lapses_min": int(self.h_lapses.value()),
            "hard_ease_max_pct": int(self.h_ease_max.value()),

            "easy_lapses_max": int(self.e_lapses_max.value()),
            "easy_ivl_min": int(self.e_ivl_min.value()),
            "easy_ease_min_pct": int(self.e_ease_min.value()),

            "very_easy_ivl_min": int(self.ve_ivl_min.value()),
            "very_easy_ease_min_pct": int(self.ve_ease_min.value()),
        }

        _write_config_keep_unknown(updated)
        tooltip("Settings saved.")
        self.accept()


def open_settings_dialog() -> None:
    d = ConfigDialog(parent=mw)
    d.exec()


def register_custom_config_gui() -> None:
    """
    Register custom config action so the add-on's "Config" button opens our dialog.
    This does NOT add a Tools menu action.
    """
    try:
        mw.addonManager.setConfigAction(__name__, open_settings_dialog)
    except Exception:
        # If API not available, silently fall back to default JSON editor.
        pass


# =====================================
# UI (Tools menu actions for running ops)
# =====================================
def set_difficulty_tags():
    cfg = get_cfg()

    search, ok = getText(
        "Enter a search query to select which cards to tag.\n"
        "Leave empty to target all cards.",
        default="",
        title="Auto-assign difficulty tags (5 levels)",
    )
    if not ok:
        return

    def on_success(processed: int):
        if processed == 0:
            tooltip("No cards matched the search.")
        else:
            tooltip(f"Assigned 5-level difficulty tags to {processed} notes.")
        mw.reset()

    QueryOp(
        parent=mw,
        op=lambda col: _assign_difficulty_tags(col, search, cfg),
        success=on_success,
    ).with_progress(label="Assigning 5-level difficulty tags…").run_in_background()


def add_menu_button():
    # Keep existing Tools actions (no new Settings item)
    action_assign = QAction("Auto-assign difficulty tags (5 levels)", mw)
    action_assign.triggered.connect(set_difficulty_tags)
    mw.form.menuTools.addAction(action_assign)


# Register GUI + menu actions
register_custom_config_gui()
add_menu_button()
