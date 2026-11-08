"""Text and number formatting helpers shared by the core and the UI."""

from __future__ import annotations

import math


def normalize(s: str) -> str:
    """Strip and collapse inner whitespace (D3)."""
    return " ".join(s.split())


def fmt_num(x: float | None) -> str:
    """Format a number for display: ``10``, ``2.5``, ``∞`` or ``—``."""
    if x is None:
        return "—"
    if isinstance(x, float) and math.isinf(x):
        return "∞" if x > 0 else "-∞"
    if isinstance(x, float) and math.isnan(x):
        return "NaN"
    if float(x).is_integer():
        return str(int(x))
    return format(x, ".10g")
