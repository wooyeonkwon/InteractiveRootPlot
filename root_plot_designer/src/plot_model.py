from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np


@dataclass
class Hist1DData:
    name: str
    edges: np.ndarray
    values: np.ndarray
    errors: np.ndarray

    def to_payload(self) -> Dict:
        return {
            "kind": "TH1",
            "name": self.name,
            "edges": self.edges.tolist(),
            "values": self.values.tolist(),
            "errors": self.errors.tolist(),
        }

    @classmethod
    def from_payload(cls, payload: Dict) -> "Hist1DData":
        return cls(
            name=payload["name"],
            edges=np.array(payload["edges"], dtype=float),
            values=np.array(payload["values"], dtype=float),
            errors=np.array(payload["errors"], dtype=float),
        )


@dataclass
class RootObjectMeta:
    name: str
    class_name: str
    title: str


def downsample_points(x: np.ndarray, y: np.ndarray, n_max: Optional[int]) -> tuple[np.ndarray, np.ndarray]:
    if not n_max or len(x) <= n_max:
        return x, y
    idx = np.linspace(0, len(x) - 1, n_max, dtype=int)
    return x[idx], y[idx]


def marker_symbol_map(marker_style: str) -> str:
    mapping = {
        "circle": "circle",
        "square": "square",
        "diamond": "diamond",
        "cross": "cross",
        "x": "x",
        "triangle-up": "triangle-up",
    }
    return mapping.get(marker_style, "circle")
