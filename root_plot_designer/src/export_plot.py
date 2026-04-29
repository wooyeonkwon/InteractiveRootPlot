from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt

from .layout_schema import LayoutModel
from .plot_model import Hist1DData


def export_layout_matplotlib(histograms: Dict[str, Hist1DData], layout: LayoutModel, out_path: str) -> str:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(layout.canvas.width / 100.0, layout.canvas.height / 100.0), dpi=100)
    for pad in layout.pads:
        x1, y1, x2, y2 = pad.coords
        ax = fig.add_axes([x1, y1, x2 - x1, y2 - y1])
        ax.set_xmargin(pad.margin_x)
        ax.set_ymargin(pad.margin_y)
        ax.set_xscale("log" if pad.logx else "linear")
        ax.set_yscale("log" if pad.logy else "linear")

        plotted = 0
        for obj in pad.objects:
            hist = histograms.get(obj.root_object_path)
            if hist is None:
                continue
            centers = 0.5 * (hist.edges[1:] + hist.edges[:-1])
            color = obj.style.get("line_color", "#1f77b4")
            marker_size = obj.style.get("marker_size", 7)
            ax.errorbar(
                centers,
                hist.values,
                yerr=hist.errors,
                fmt="o",
                color=color,
                markersize=marker_size,
                label=obj.legend_label or obj.root_object_path,
            )
            plotted += 1
        if plotted > 0:
            ax.legend(loc="upper left")

        for label in [x for x in layout.labels if x.target_pad == pad.pad_id]:
            ha = {"left": "left", "center": "center", "right": "right"}.get(label.alignment, "left")
            ax.text(label.position[0], label.position[1], label.text, transform=ax.transAxes, fontsize=label.font_size, ha=ha, va="top")

    fig.savefig(out)
    plt.close(fig)
    return str(out)


def build_repro_script(root_path: str, layout: LayoutModel) -> str:
    return f'''#!/usr/bin/env python3
import uproot
import numpy as np
import matplotlib.pyplot as plt

ROOT_FILE = {root_path!r}
LAYOUT = {layout.to_dict()!r}

with uproot.open(ROOT_FILE) as f:
    cache = {{}}
    for pad in LAYOUT['pads']:
        for obj in pad.get('objects', []):
            key = obj['root_object_path']
            if key in cache:
                continue
            h = f[key]
            values, edges = h.to_numpy(flow=False)
            variances = h.variances(flow=False)
            errors = np.sqrt(variances) if variances is not None else np.sqrt(np.clip(values, 0, None))
            cache[key] = (edges, values, errors)

fig = plt.figure(figsize=(LAYOUT['canvas']['width'] / 100.0, LAYOUT['canvas']['height'] / 100.0), dpi=100)
for pad in LAYOUT['pads']:
    x1, y1, x2, y2 = pad['coords']
    ax = fig.add_axes([x1, y1, x2-x1, y2-y1])
    ax.set_xscale('log' if pad.get('logx') else 'linear')
    ax.set_yscale('log' if pad.get('logy') else 'linear')
    for obj in pad.get('objects', []):
        edges, values, errors = cache[obj['root_object_path']]
        centers = 0.5 * (edges[1:] + edges[:-1])
        s = obj.get('style', {{}})
        ax.errorbar(centers, values, yerr=errors, fmt='o', color=s.get('line_color', '#1f77b4'), markersize=s.get('marker_size', 7), label=obj.get('legend_label') or obj['root_object_path'])
    if pad.get('objects'):
        ax.legend(loc='upper left')

    for label in LAYOUT.get('labels', []):
        if label.get('target_pad') != pad.get('pad_id'):
            continue
        ha = {{'left': 'left', 'center': 'center', 'right': 'right'}}.get(label.get('alignment', 'left'), 'left')
        px, py = label.get('position', [0.02, 0.98])
        ax.text(px, py, label.get('text', ''), transform=ax.transAxes, fontsize=label.get('font_size', 11), ha=ha, va='top')

fig.savefig('reproduced_plot.png')
fig.savefig('reproduced_plot.pdf')
fig.savefig('reproduced_plot.svg')
print('Saved reproduced_plot.(png|pdf|svg)')
'''
