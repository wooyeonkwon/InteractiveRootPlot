from __future__ import annotations

from typing import List

import numpy as np
import uproot

from .plot_model import Hist1DData, RootObjectMeta


SUPPORTED_CLASSES = ("TH1", "TH1F", "TH1D", "TH1I", "TH1S")


def list_objects(root_path: str) -> List[RootObjectMeta]:
    metas: List[RootObjectMeta] = []
    with uproot.open(root_path) as f:
        for key, classname in f.classnames().items():
            if classname.startswith("TH1") or classname.startswith("TH2") or classname.startswith("TGraph"):
                obj = f[key]
                metas.append(
                    RootObjectMeta(
                        name=key.split(";")[0],
                        class_name=classname,
                        title=getattr(obj, "title", ""),
                    )
                )
    return metas


def load_th1(root_path: str, object_name: str) -> Hist1DData:
    with uproot.open(root_path) as f:
        h = f[object_name]
        values, edges = h.to_numpy(flow=False)
        variances = h.variances(flow=False)
        errors = np.sqrt(variances) if variances is not None else np.sqrt(np.clip(values, 0, None))
        return Hist1DData(name=object_name, edges=np.asarray(edges), values=np.asarray(values), errors=np.asarray(errors))
