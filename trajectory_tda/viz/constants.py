"""
Shared constants for trajectory TDA publication figures.

Defines color palettes, figure dimensions, and matplotlib RC params
following Journal of Economic Geography submission standards.
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────
# 9-state categorical palette
# Employment (E) = greens, Unemployment (U) = reds/oranges,
# Inactivity (I) = blues. L/M/H = dark/medium/light.
# ─────────────────────────────────────────────────────────────────────

STATE_COLORS: dict[str, str] = {
    "EL": "#2d6a2e",  # forest green
    "EM": "#4caf50",  # medium green
    "EH": "#a5d6a7",  # light green
    "UL": "#b71c1c",  # dark red
    "UM": "#ff5722",  # orange-red
    "UH": "#ffc107",  # gold
    "IL": "#1a237e",  # dark blue
    "IM": "#42a5f5",  # medium blue
    "IH": "#90caf9",  # light blue
}

STATES = ["EL", "EM", "EH", "UL", "UM", "UH", "IL", "IM", "IH"]

STATE_LABELS: dict[str, str] = {
    "EL": "Employed Low",
    "EM": "Employed Mid",
    "EH": "Employed High",
    "UL": "Unemployed Low",
    "UM": "Unemployed Mid",
    "UH": "Unemployed High",
    "IL": "Inactive Low",
    "IM": "Inactive Mid",
    "IH": "Inactive High",
}

# ─────────────────────────────────────────────────────────────────────
# Regime labels (from empirical results)
# ─────────────────────────────────────────────────────────────────────

REGIME_LABELS: dict[int, str] = {
    0: "Mixed Churn",
    1: "Secure EH",
    2: "Inactive Low",
    3: "Emp-Inactive Mix",
    4: "Employed Mid",
    5: "High-Income Inactive",
    6: "Low-Income Churn",
}

# ─────────────────────────────────────────────────────────────────────
# Figure dimensions (Journal of Economic Geography)
# ─────────────────────────────────────────────────────────────────────

# 190mm full width, 90mm half width — converted to inches
MM_TO_INCHES = 1 / 25.4
FULL_WIDTH = 190 * MM_TO_INCHES  # ~7.48 inches
HALF_WIDTH = 90 * MM_TO_INCHES  # ~3.54 inches
COLUMN_HEIGHT = 120 * MM_TO_INCHES  # ~4.72 inches

FIGSIZE_FULL = (FULL_WIDTH, COLUMN_HEIGHT)
FIGSIZE_HALF = (HALF_WIDTH, COLUMN_HEIGHT)
FIGSIZE_WIDE = (FULL_WIDTH, FULL_WIDTH * 0.55)
FIGSIZE_SQUARE = (HALF_WIDTH, HALF_WIDTH)

DPI = 300

# ─────────────────────────────────────────────────────────────────────
# Matplotlib RC params for publication
# ─────────────────────────────────────────────────────────────────────

PUBLICATION_RC = {
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.dpi": DPI,
    "savefig.dpi": DPI,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    "axes.linewidth": 0.8,
    "lines.linewidth": 1.2,
    "pdf.fonttype": 42,  # TrueType fonts in PDF (editable text)
    "ps.fonttype": 42,
}
