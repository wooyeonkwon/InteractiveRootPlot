from __future__ import annotations

from pathlib import Path
from io import BytesIO
from typing import Dict

import matplotlib.pyplot as plt
import numpy as np

from .layout_schema import LayoutModel
from .plot_model import Hist1DData


def _to_mpl_marker(marker_style: str) -> str:
    mapping = {
        "circle": "o",
        "square": "s",
        "diamond": "D",
        "cross": "+",
        "x": "x",
        "triangle-up": "^",
    }
    return mapping.get(marker_style, marker_style if marker_style else "o")


def _apply_transform(hist: Hist1DData, obj):
    edges, values, errors = hist.edges.copy(), hist.values.copy(), hist.errors.copy()
    if obj.rebin_edges:
        new_edges = obj.rebin_edges
        centers = 0.5 * (edges[1:] + edges[:-1])
        new_values = []
        new_errors = []
        for i in range(len(new_edges) - 1):
            mask = (centers >= new_edges[i]) & (centers < new_edges[i + 1])
            v = values[mask].sum()
            e = (errors[mask] ** 2).sum() ** 0.5
            new_values.append(v)
            new_errors.append(e)
        edges = np.array(new_edges, dtype=float)
        values = np.array(new_values, dtype=float)
        errors = np.array(new_errors, dtype=float)
    elif obj.rebin_factor and obj.rebin_factor > 1:
        k = int(obj.rebin_factor)
        n = (len(values) // k) * k
        values = values[:n].reshape(-1, k).sum(axis=1)
        errors = (errors[:n].reshape(-1, k) ** 2).sum(axis=1) ** 0.5
        edges = edges[::k]
        if len(edges) != len(values) + 1:
            edges = np.append(edges, hist.edges[n])

    widths = edges[1:] - edges[:-1]
    if obj.normalization == "area":
        area = values.sum()
        if area > 0:
            values, errors = values / area, errors / area
    elif obj.normalization == "scale":
        values, errors = values * obj.scale_factor, errors * obj.scale_factor
    elif obj.normalization == "bin_width":
        nonzero = widths > 0
        values[nonzero], errors[nonzero] = values[nonzero] / widths[nonzero], errors[nonzero] / widths[nonzero]
    return edges, values, errors


def _render_layout_figure(histograms: Dict[str, Hist1DData], layout: LayoutModel):
    fig = plt.figure(figsize=(layout.canvas.width / 100.0, layout.canvas.height / 100.0), dpi=100)
    for pad in layout.pads:
        if len(pad.coords) != 4:
            continue
        x1, y1, x2, y2 = pad.coords
        if x2 <= x1 or y2 <= y1:
            continue
        ratio_ax = None
        if pad.ratio_enabled:
            h = (y2 - y1)
            ratio_h = 0.28 * h
            main_h = h - ratio_h - 0.01
            ax = fig.add_axes([x1, y1 + ratio_h + 0.01, x2 - x1, main_h])
            ratio_ax = fig.add_axes([x1, y1, x2 - x1, ratio_h], sharex=ax)
            ax.tick_params(labelbottom=False)
            ratio_ax.set_ylabel("Ratio")
            ratio_ax.set_ylim(pad.ratio_y_min, pad.ratio_y_max)
        else:
            ax = fig.add_axes([x1, y1, x2 - x1, y2 - y1])
        ax.set_xmargin(pad.margin_x)
        ax.set_ymargin(pad.margin_y)
        ax.set_xscale("log" if pad.logx else "linear")
        ax.set_yscale("log" if pad.logy else "linear")
        if pad.x_title and ratio_ax is None:
            ax.set_xlabel(pad.x_title)
        if pad.x_title and ratio_ax is not None:
            ratio_ax.set_xlabel(pad.x_title)
        if pad.y_title:
            ax.set_ylabel(pad.y_title)
        if pad.x_min is not None and pad.x_max is not None:
            ax.set_xlim(pad.x_min, pad.x_max)
        if pad.y_min is not None and pad.y_max is not None:
            ax.set_ylim(pad.y_min, pad.y_max)

        ymins, ymaxs = [], []
        legend_handles = []
        transformed = {}
        for obj in pad.objects:
            if not obj.visible:
                continue
            hist = histograms.get(obj.root_object_path)
            if hist is None:
                continue
            edges, values, errors = _apply_transform(hist, obj)
            transformed[obj.root_object_path] = (edges, values, errors, obj)
            centers = 0.5 * (edges[1:] + edges[:-1])
            color = obj.style.get("line_color", "#1f77b4")
            marker = _to_mpl_marker(obj.style.get("marker_style", "o"))
            h = ax.errorbar(
                centers,
                values,
                yerr=errors,
                fmt="none",
                color=color,
                marker=marker,
                markersize=obj.style.get("marker_size", 7),
                linewidth=obj.style.get("line_width", 1.5),
                linestyle=obj.style.get("line_style", "-"),
                markerfacecolor=obj.style.get("marker_color", color),
                markeredgecolor=obj.style.get("marker_color", color),
                alpha=obj.style.get("fill_alpha", 1.0),
                label=obj.legend_label or obj.root_object_path,
            )
            if obj.style.get("fill_color"):
                ax.fill_between(centers, values, color=obj.style.get("fill_color"), alpha=obj.style.get("fill_alpha", 0.3))
            legend_handles.append(h)
            pos = values[values > 0] if pad.logy else values
            if len(pos):
                ymins.append(float(pos.min()))
                ymaxs.append(float(pos.max()))
            if ratio_ax is not None and pad.ratio_reference and obj.root_object_path != pad.ratio_reference:
                ref = transformed.get(pad.ratio_reference)
                if ref is not None and len(ref[1]) == len(values):
                    ref_values = ref[1]
                    ref_errors = ref[2]
                    safe = ref_values != 0
                    ratio = np.zeros_like(values, dtype=float)
                    ratio_err = np.zeros_like(errors, dtype=float)
                    ratio[safe] = values[safe] / ref_values[safe]
                    ratio_err[safe] = np.sqrt((errors[safe] / ref_values[safe]) ** 2 + ((values[safe] * ref_errors[safe]) / (ref_values[safe] ** 2)) ** 2)
                    ratio_ax.errorbar(
                        centers[safe],
                        ratio[safe],
                        yerr=ratio_err[safe],
                        fmt="none",
                        marker=marker,
                        color=color,
                        markersize=obj.style.get("marker_size", 5),
                        linewidth=obj.style.get("line_width", 1.2),
                        linestyle=obj.style.get("line_style", "-"),
                    )
        if ymins and ymaxs and (pad.y_min is None or pad.y_max is None):
            ymin = min(ymins)
            ymax = max(ymaxs)
            if pad.logy:
                ymin = max(ymin, 1e-9)
                ax.set_ylim(ymin * 0.8, ymax * 1.5)
            else:
                ax.set_ylim(min(0.0, ymin * 0.9), ymax * 1.2)
        if pad.legend.show and legend_handles:
            handles = legend_handles[::-1] if pad.legend.entry_order == "reverse" else legend_handles
            leg = ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(pad.legend.position[0], pad.legend.position[1], pad.legend.position[2]-pad.legend.position[0], pad.legend.position[3]-pad.legend.position[1]), fontsize=pad.legend.text_size)
            leg.get_frame().set_linewidth(1.0 if pad.legend.border else 0.0)
            if pad.legend.fill_transparent:
                leg.get_frame().set_alpha(0.0)

        for label in [x for x in layout.labels if x.target_pad == pad.pad_id]:
            ha = {"left": "left", "center": "center", "right": "right"}.get(label.alignment, "left")
            ax.text(label.position[0], label.position[1], label.text, transform=ax.transAxes, fontsize=label.font_size, ha=ha, va="top")

    return fig


def render_layout_png_bytes(histograms: Dict[str, Hist1DData], layout: LayoutModel) -> bytes:
    fig = _render_layout_figure(histograms, layout)
    buf = BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def export_layout_matplotlib(histograms: Dict[str, Hist1DData], layout: LayoutModel, out_path: str) -> str:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig = _render_layout_figure(histograms, layout)
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
