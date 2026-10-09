from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml


def normalize_key(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[-'’]", " ", s)
    return re.sub(r"\s+", " ", s).strip().upper()


@dataclass(frozen=True)
class Family:
    id: str
    label: str
    position: float | None
    color: str


@dataclass(frozen=True)
class ListMapping:
    key: str
    label: str
    family: str
    to_validate: bool = False


def _read(path: Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_families(path: Path) -> list[Family]:
    return [
        Family(f["id"], f["label"], f.get("position"), f["color"])
        for f in _read(path)["families"]
    ]


def load_list_mappings(path: Path) -> dict[str, dict[str, ListMapping]]:
    data = _read(path)
    known = {f["id"] for f in data["families"]}
    out: dict[str, dict[str, ListMapping]] = {}
    for election_id, entries in data["elections"].items():
        out[election_id] = {}
        for e in entries:
            key = normalize_key(e["key"])
            if e["family"] not in known:
                raise ValueError(f"{election_id}/{key}: famille inconnue {e['family']!r}")
            if key in out[election_id]:
                raise ValueError(f"{election_id}: clé en double {key!r}")
            out[election_id][key] = ListMapping(key, e["label"], e["family"], bool(e.get("to_validate", False)))
    return out
