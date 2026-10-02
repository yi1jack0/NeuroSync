"""Design tokens + Qt stylesheet.

Qt has no backdrop blur, so "glass" is built from three layers:
  1. an aurora backdrop painted behind everything (soft blobs in the band colour),
  2. panels filled with low-alpha white and a 1px hairline border,
  3. a slightly brighter top edge on panels (light catching the glass).
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor

from ..domain.bands import BrainwaveBand

BAND_COLORS = {
    BrainwaveBand.DELTA: "#7B61FF",   # deep purple - sleep
    BrainwaveBand.THETA: "#B18CFF",   # lavender - meditation
    BrainwaveBand.ALPHA: "#2DD4E8",   # cyan - calm focus
    BrainwaveBand.BETA:  "#3EE0A1",   # mint - active focus
    BrainwaveBand.GAMMA: "#F7B955",   # amber - creativity
}

CATEGORY_ORDER = ["Sleep", "Meditate", "Focus", "Creativity"]
BAND_CATEGORY = {BrainwaveBand.DELTA: "Sleep", BrainwaveBand.THETA: "Meditate",
                 BrainwaveBand.ALPHA: "Focus", BrainwaveBand.BETA: "Focus",
                 BrainwaveBand.GAMMA: "Creativity"}

FONT_FAMILIES = ["Segoe UI Variable Text", "Segoe UI", "Inter", "DejaVu Sans", "sans-serif"]


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str            # window base
    bg_deep: str       # vignette edge
    panel: str         # glass fill (rgba)
    panel_hover: str
    border: str        # hairline
    border_top: str    # lit top edge
    text: str
    text_dim: str
    text_faint: str
    danger: str
    focus: str         # keyboard focus ring (None = accent)
    glass: bool        # draw translucent layers / aurora
    surface: str = "#1A1D22"   # opaque popups: menus, cards, toasts


DARK = Palette(
    name="dark", bg="#121417", bg_deep="#0B0C0E",
    panel="rgba(255,255,255,0.045)", panel_hover="rgba(255,255,255,0.08)",
    border="rgba(255,255,255,0.08)", border_top="rgba(255,255,255,0.14)",
    text="#E9ECF1", text_dim="#9AA3AF", text_faint="#5E6672",
    danger="#FF6B7A", focus="", glass=True)

HIGH_CONTRAST = Palette(
    name="high-contrast", bg="#000000", bg_deep="#000000",
    panel="#000000", panel_hover="#1A1A1A",
    border="#FFFFFF", border_top="#FFFFFF",
    text="#FFFFFF", text_dim="#FFFFFF", text_faint="#C8C8C8",
    danger="#FF8080", focus="#FFFF00", glass=False, surface="#000000")


def band_color(band: BrainwaveBand) -> QColor:
    return QColor(BAND_COLORS[band])


def rgba(color: QColor | str, alpha: float) -> str:
    c = QColor(color)
    return f"rgba({c.red()},{c.green()},{c.blue()},{alpha:.3f})"


def stylesheet(p: Palette, accent: QColor | str) -> str:
    a = QColor(accent) if p.glass else QColor("#FFFF00")
    acc, acc_soft, acc_line = a.name(), rgba(a, 0.16), rgba(a, 0.45)
    focus = p.focus or acc
    on_accent = "#0B0C0E"
    return f"""
* {{ color: {p.text}; font-size: 10pt; outline: none; }}
QMainWindow, #Root {{ background: {p.bg}; }}
QToolTip {{ background: {p.surface}; color: {p.text}; border: 1px solid {p.border};
           padding: 6px 8px; border-radius: 6px; }}

/* ---------- glass panels ---------- */
#GlassPanel {{ background: {p.panel}; border: 1px solid {p.border};
              border-top-color: {p.border_top}; border-radius: 16px; }}
#TopBar {{ background: {p.panel}; border: 1px solid {p.border};
          border-top-color: {p.border_top}; border-radius: 14px; }}

/* ---------- typography ---------- */
#Wordmark {{ font-size: 13pt; font-weight: 600; letter-spacing: 0.5px; }}
#WordmarkAccent {{ font-size: 13pt; font-weight: 300; color: {acc}; }}
#SectionTitle {{ color: {p.text_dim}; font-size: 8pt; font-weight: 600;
                letter-spacing: 1.6px; }}
#PresetTitle {{ font-size: 22pt; font-weight: 300; }}
#PresetMeta {{ color: {p.text_dim}; font-size: 10.5pt; }}
#BandChip {{ color: {acc}; background: {acc_soft}; border: 1px solid {acc_line};
            border-radius: 11px; padding: 3px 12px; font-size: 9pt; font-weight: 600;
            letter-spacing: 1px; }}
#Dim {{ color: {p.text_dim}; }}
#Faint {{ color: {p.text_faint}; font-size: 9pt; }}
#Countdown {{ font-size: 11pt; font-weight: 500; color: {acc};
             font-family: "Cascadia Mono", "Consolas", "DejaVu Sans Mono"; }}
#StripValue {{ font-size: 10.5pt; font-weight: 600;
              font-family: "Cascadia Mono", "Consolas", "DejaVu Sans Mono"; }}
#StripLabel {{ color: {p.text_dim}; font-size: 8.5pt; }}
#StripBand {{ font-size: 8pt; font-weight: 700; letter-spacing: 1px; }}

/* ---------- buttons ---------- */
QPushButton, QToolButton {{ background: {p.panel}; border: 1px solid {p.border};
    border-radius: 10px; padding: 7px 14px; }}
QPushButton:hover, QToolButton:hover {{ background: {p.panel_hover}; }}
QPushButton:pressed, QToolButton:pressed {{ background: {acc_soft}; }}
QPushButton:focus, QToolButton:focus, QComboBox:focus, QLineEdit:focus,
QListWidget:focus {{ border: 2px solid {focus}; }}
QPushButton:disabled {{ color: {p.text_faint}; }}
QToolButton::menu-indicator {{ image: none; width: 0; }}

#PlayButton {{ background: {acc}; border: none; border-radius: 26px; }}
#PlayButton:hover {{ background: {a.lighter(115).name()}; }}
#PlayButton:pressed {{ background: {a.darker(110).name()}; }}
#PlayButton:focus {{ border: 3px solid {p.text}; }}
#IconButton {{ background: transparent; border: 1px solid transparent; border-radius: 10px;
              padding: 6px; }}
#IconButton:hover {{ background: {p.panel_hover}; border-color: {p.border}; }}
#IconButton:checked {{ background: {acc_soft}; border-color: {acc_line}; }}
#IconButton:focus {{ border: 2px solid {focus}; }}
#Primary {{ background: {acc}; color: {on_accent}; border: none; font-weight: 600; }}
#Primary:hover {{ background: {a.lighter(112).name()}; }}
#Primary:focus {{ border: 2px solid {p.text}; }}
#Ghost {{ background: transparent; border: 1px dashed {p.border_top}; color: {p.text_dim}; }}
#Ghost:hover {{ color: {p.text}; border-color: {acc_line}; background: {acc_soft}; }}
#Chip {{ border-radius: 14px; padding: 5px 12px; }}
#Chip:checked {{ background: {acc_soft}; border-color: {acc_line}; color: {acc}; }}

/* ---------- inputs ---------- */
QComboBox {{ background: {p.panel}; border: 1px solid {p.border}; border-radius: 10px;
            padding: 6px 12px; min-width: 150px; }}
QComboBox:hover {{ background: {p.panel_hover}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {p.surface}; border: 1px solid {p.border};
    selection-background-color: {acc_soft}; selection-color: {p.text}; padding: 4px; }}
QLineEdit, QSpinBox {{ background: rgba(0,0,0,0.25); border: 1px solid {p.border};
    border-radius: 8px; padding: 6px 10px; selection-background-color: {acc_line}; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 5px;
    border: 1px solid {p.border_top}; background: rgba(0,0,0,0.2); }}
QCheckBox::indicator:checked {{ background: {acc}; border-color: {acc}; }}
QCheckBox:focus {{ color: {focus}; }}

/* ---------- menus ---------- */
QMenu {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 7px 26px 7px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: {acc_soft}; }}
QMenu::separator {{ height: 1px; background: {p.border}; margin: 5px 8px; }}
QMenu::indicator {{ width: 14px; height: 14px; left: 6px; }}

/* ---------- preset library ---------- */
QListWidget {{ background: transparent; border: none; }}
QListWidget::item {{ border-radius: 10px; padding: 0px; margin: 1px 0; }}
QListWidget::item:hover {{ background: {p.panel_hover}; }}
QListWidget::item:selected {{ background: {acc_soft}; }}

QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QScrollBar:vertical, QScrollBar:horizontal {{ background: transparent; width: 8px; height: 8px; }}
QScrollBar::handle {{ background: {p.border_top}; border-radius: 4px; min-height: 30px;
                     min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------- overlays ---------- */
#Card {{ background: {p.surface}; border: 1px solid {p.border_top}; border-radius: 20px; }}
#Toast {{ background: {p.surface}; border: 1px solid {p.border_top}; border-radius: 12px; }}
#ToastAction {{ background: transparent; border: none; color: {acc}; font-weight: 600;
               padding: 4px 8px; }}
#Kbd {{ background: rgba(255,255,255,0.06); border: 1px solid {p.border};
       border-bottom-width: 2px; border-radius: 6px; padding: 2px 8px;
       font-family: "Cascadia Mono", "Consolas", "DejaVu Sans Mono"; font-size: 9pt; }}
"""


def strip_qss(p: Palette, accent: QColor | str) -> str:
    """Extra rules for mixer strips (kept separate so the main sheet stays readable)."""
    a = QColor(accent) if p.glass else QColor("#FFFF00")
    return f"""
#Strip {{ background: {p.panel}; border: 1px solid {p.border}; border-radius: 12px; }}
#Strip[generator="true"] {{ background: {rgba(a, 0.06) if p.glass else p.panel};
                           border-color: {rgba(a, 0.22) if p.glass else p.border}; }}
#Strip:hover {{ border-color: {p.border_top}; }}
#Divider {{ background: {p.border}; max-height: 1px; min-height: 1px; }}
#SearchField {{ background: rgba(0,0,0,0.22); border-radius: 10px; padding: 7px 12px; }}
"""
