from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from .plot_model import Hist1DData
from .style_schema import PlotStyle


def export_hist1_matplotlib(hist: Hist1DData, style: PlotStyle, out_path: str) -> str:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    centers = 0.5 * (hist.edges[1:] + hist.edges[:-1])
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.errorbar(
        centers,
        hist.values,
        yerr=hist.errors,
        fmt="o",
        color=style.line_color,
        markersize=style.marker_size,
        label=style.legend_text or hist.name,
    )
    ax.set_xlabel(style.x_title or "X")
    ax.set_ylabel(style.y_title or "Entries")
    if style.x_min is not None and style.x_max is not None:
        ax.set_xlim(style.x_min, style.x_max)
    if style.y_min is not None and style.y_max is not None:
        ax.set_ylim(style.y_min, style.y_max)
    ax.set_yscale("log" if style.log_y else "linear")
    ax.legend(loc="upper left")
    ax.text(0.02, 0.98, style.cms_label, transform=ax.transAxes, va="top", ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return str(out)


def build_repro_script(root_path: str, object_name: str, style: PlotStyle) -> str:
    return f'''#!/usr/bin/env python3
import uproot
import numpy as np
import matplotlib.pyplot as plt

ROOT_FILE = {root_path!r}
OBJECT_NAME = {object_name!r}
STYLE = {style.to_dict()!r}

with uproot.open(ROOT_FILE) as f:
    h = f[OBJECT_NAME]
    values, edges = h.to_numpy(flow=False)
    variances = h.variances(flow=False)
    errors = np.sqrt(variances) if variances is not None else np.sqrt(np.clip(values, 0, None))

centers = 0.5 * (edges[1:] + edges[:-1])
fig, ax = plt.subplots(figsize=(8, 6))
ax.errorbar(centers, values, yerr=errors, fmt='o', color=STYLE['line_color'], markersize=STYLE['marker_size'], label=STYLE['legend_text'] or OBJECT_NAME)
ax.set_xlabel(STYLE['x_title'] or 'X')
ax.set_ylabel(STYLE['y_title'] or 'Entries')
if STYLE.get('x_min') is not None and STYLE.get('x_max') is not None:
    ax.set_xlim(STYLE['x_min'], STYLE['x_max'])
if STYLE.get('y_min') is not None and STYLE.get('y_max') is not None:
    ax.set_ylim(STYLE['y_min'], STYLE['y_max'])
ax.set_yscale('log' if STYLE.get('log_y') else 'linear')
ax.legend(loc='upper left')
ax.text(0.02, 0.98, STYLE.get('cms_label', 'CMS Preliminary'), transform=ax.transAxes, va='top', ha='left', fontsize=11, fontweight='bold')
fig.tight_layout()
fig.savefig('reproduced_plot.png')
fig.savefig('reproduced_plot.pdf')
fig.savefig('reproduced_plot.svg')
print('Saved reproduced_plot.(png|pdf|svg)')
'''
