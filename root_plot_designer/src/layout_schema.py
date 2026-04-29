from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlotObjectConfig:
    root_object_path: str
    draw_option: str = "E1"
    legend_label: str = ""
    style: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LabelConfig:
    text: str
    target_pad: str
    position: List[float] = field(default_factory=lambda: [0.02, 0.98])
    font_size: float = 11.0
    alignment: str = "left"


@dataclass
class PadConfig:
    pad_id: str
    coords: List[float] = field(default_factory=lambda: [0.12, 0.12, 0.95, 0.92])
    margin_x: float = 0.12
    margin_y: float = 0.10
    logx: bool = False
    logy: bool = False
    logz: bool = False
    x_title: str = ""
    y_title: str = ""
    x_min: Optional[float] = None
    x_max: Optional[float] = None
    y_min: Optional[float] = None
    y_max: Optional[float] = None
    objects: List[PlotObjectConfig] = field(default_factory=list)


@dataclass
class CanvasConfig:
    width: int = 800
    height: int = 600


@dataclass
class LayoutModel:
    canvas: CanvasConfig = field(default_factory=CanvasConfig)
    pads: List[PadConfig] = field(default_factory=lambda: [PadConfig(pad_id="pad1")])
    labels: List[LabelConfig] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Optional[Dict[str, Any]]) -> "LayoutModel":
        raw = raw or {}
        canvas_raw = raw.get("canvas", {})
        canvas = CanvasConfig(
            width=int(canvas_raw.get("width", 800)),
            height=int(canvas_raw.get("height", 600)),
        )
        pads: List[PadConfig] = []
        for i, p in enumerate(raw.get("pads", []), start=1):
            objs = [
                PlotObjectConfig(
                    root_object_path=o.get("root_object_path", ""),
                    draw_option=o.get("draw_option", "E1"),
                    legend_label=o.get("legend_label", ""),
                    style=o.get("style", {}) or {},
                )
                for o in p.get("objects", [])
            ]
            pads.append(
                PadConfig(
                    pad_id=p.get("pad_id", f"pad{i}"),
                    coords=p.get("coords", [0.12, 0.12, 0.95, 0.92]),
                    margin_x=float(p.get("margin_x", 0.12)),
                    margin_y=float(p.get("margin_y", 0.10)),
                    logx=bool(p.get("logx", False)),
                    logy=bool(p.get("logy", False)),
                    logz=bool(p.get("logz", False)),
                    x_title=p.get("x_title", ""),
                    y_title=p.get("y_title", ""),
                    x_min=p.get("x_min"),
                    x_max=p.get("x_max"),
                    y_min=p.get("y_min"),
                    y_max=p.get("y_max"),
                    objects=objs,
                )
            )
        if not pads:
            pads = [PadConfig(pad_id="pad1")]

        labels = [
            LabelConfig(
                text=l.get("text", ""),
                target_pad=l.get("target_pad", "pad1"),
                position=l.get("position", [0.02, 0.98]),
                font_size=float(l.get("font_size", 11.0)),
                alignment=l.get("alignment", "left"),
            )
            for l in raw.get("labels", [])
        ]
        return cls(canvas=canvas, pads=pads, labels=labels)
