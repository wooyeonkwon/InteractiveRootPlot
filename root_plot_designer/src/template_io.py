from __future__ import annotations

import json
from typing import Dict

import yaml


def dump_template(style: Dict, fmt: str = "yaml") -> str:
    if fmt == "json":
        return json.dumps(style, indent=2, ensure_ascii=False)
    return yaml.safe_dump(style, sort_keys=False, allow_unicode=True)


def load_template(raw: str) -> Dict:
    raw = raw.strip()
    if not raw:
        return {}
    if raw.startswith("{"):
        return json.loads(raw)
    return yaml.safe_load(raw)
