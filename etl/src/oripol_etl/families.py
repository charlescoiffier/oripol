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


def load_list_mappings(path: Path, known_families: set[str]) -> dict[str, dict[str, ListMapping]]:
    """Rattachement liste/candidat → famille, par élection.

    Deux formes de fichier :
    - `elections:` : rattachement explicite élection par élection (présidentielle, par nom de candidat) ;
    - `nuances:` + `applies_to:` : un même tableau nuance → famille appliqué à plusieurs élections.
    """
    data = _read(path)
    out: dict[str, dict[str, ListMapping]] = {}

    def add(election_id: str, entries: list[dict]) -> None:
        out[election_id] = {}
        for e in entries:
            key = normalize_key(e["key"])
            if e["family"] not in known_families:
                raise ValueError(f"{election_id}/{key}: famille inconnue {e['family']!r}")
            if key in out[election_id]:
                raise ValueError(f"{election_id}: clé en double {key!r}")
            out[election_id][key] = ListMapping(key, e["label"], e["family"], bool(e.get("to_validate", False)))

    for election_id, entries in data.get("elections", {}).items():
        add(election_id, entries)
    if "nuances" in data:
        entries = [{"key": code, **spec} for code, spec in data["nuances"].items()]
        for election_id in data["applies_to"]:
            add(election_id, entries)
    return out


def load_all_mappings(paths: list[Path], known_families: set[str]) -> dict[str, dict[str, ListMapping]]:
    merged: dict[str, dict[str, ListMapping]] = {}
    for path in paths:
        for election_id, lists in load_list_mappings(path, known_families).items():
            if election_id in merged:
                raise ValueError(f"élection définie deux fois : {election_id}")
            merged[election_id] = lists
    return merged
