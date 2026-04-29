from __future__ import annotations

from typing import List

import numpy as np
import uproot

from .plot_model import Hist1DData, RootObjectMeta


SUPPORTED_PREFIXES = ("TH1", "TH2", "THStack", "TProfile", "TGraph")


def list_objects(root_path: str) -> List[RootObjectMeta]:
    metas: List[RootObjectMeta] = []
    with uproot.open(root_path) as f:
        for key, classname in f.classnames().items():
            if classname.startswith(SUPPORTED_PREFIXES):
                obj = f[key]
                metas.append(
                    RootObjectMeta(
                        name=key.split(";")[0],
                        class_name=classname,
                        title=getattr(obj, "title", ""),
                    )
                )
    return metas


def _x_to_edges(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return np.array([0.0, 1.0], dtype=float)
    if x.size == 1:
        return np.array([x[0] - 0.5, x[0] + 0.5], dtype=float)
    mids = 0.5 * (x[1:] + x[:-1])
    left = x[0] - (mids[0] - x[0])
    right = x[-1] + (x[-1] - mids[-1])
    return np.concatenate([[left], mids, [right]])


def load_th1(root_path: str, object_name: str) -> Hist1DData:
    with uproot.open(root_path) as f:
        obj = f[object_name]
        classname = obj.classname

        if classname.startswith("TH1") or classname.startswith("TProfile"):
            values, edges = obj.to_numpy(flow=False)
            variances = obj.variances(flow=False)
            errors = np.sqrt(variances) if variances is not None else np.sqrt(np.clip(values, 0, None))
            return Hist1DData(name=object_name, edges=np.asarray(edges), values=np.asarray(values), errors=np.asarray(errors))

        if classname.startswith("TH2") or classname.startswith("TProfile2D"):
            values, x_edges, _ = obj.to_numpy(flow=False)
            y_values = np.asarray(values, dtype=float).sum(axis=1)
            errors = np.sqrt(np.clip(y_values, 0, None))
            return Hist1DData(name=object_name, edges=np.asarray(x_edges), values=y_values, errors=errors)

        if classname.startswith("THStack"):
            hist_list = obj.member("fHists")
            if not hist_list or len(hist_list) == 0:
                raise ValueError(f"THStack '{object_name}' contains no histograms")
            total_values = None
            edges = None
            for h in hist_list:
                values, h_edges = h.to_numpy(flow=False)
                total_values = np.asarray(values, dtype=float) if total_values is None else total_values + np.asarray(values, dtype=float)
                edges = np.asarray(h_edges)
            errors = np.sqrt(np.clip(total_values, 0, None))
            return Hist1DData(name=object_name, edges=edges, values=total_values, errors=errors)

        if classname.startswith("TGraph"):
            x = np.asarray(obj.values("x"), dtype=float)
            y = np.asarray(obj.values("y"), dtype=float)
            order = np.argsort(x)
            x = x[order]
            y = y[order]
            edges = _x_to_edges(x)
            try:
                yerr = np.asarray(obj.errors("y"), dtype=float)
                if yerr.ndim > 1:
                    yerr = np.max(np.abs(yerr), axis=0)
                yerr = yerr[order]
            except Exception:
                yerr = np.zeros_like(y)
            return Hist1DData(name=object_name, edges=edges, values=y, errors=yerr)

        raise ValueError(f"Unsupported ROOT class for '{object_name}': {classname}")
