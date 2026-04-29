from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass
class PlotStyle:
    x_title: str = ""
    y_title: str = ""
    x_min: Optional[float] = None
    x_max: Optional[float] = None
    y_min: Optional[float] = None
    y_max: Optional[float] = None
    log_y: bool = False
    line_color: str = "#1f77b4"
    marker_style: str = "circle"
    marker_size: float = 7.0
    legend_text: str = ""
    legend_x: float = 0.02
    legend_y: float = 0.98
    cms_label: str = "CMS Preliminary"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "PlotStyle":
        defaults = cls().to_dict()
        defaults.update(raw or {})
        return cls(**defaults)
