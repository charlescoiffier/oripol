from __future__ import annotations

import json
from pathlib import Path

from .families import Family, ListMapping

LABELS = {"pres": "Présidentielle"}


def _parse(election_id: str) -> tuple[str, int, int]:
    kind, year, rnd = election_id.split("-")
    return kind, int(year), int(rnd)


def _label(election_id: str) -> str:
    kind, year, rnd = _parse(election_id)
    return f"{LABELS[kind]} {year} – {'1er' if rnd == 1 else f'{rnd}e'} tour"


def write_site_data(
    out: Path,
    families: list[Family],
    mappings: dict[str, dict[str, ListMapping]],
    payloads: dict[str, dict],
    names: dict[str, str],
) -> None:
    (out / "elections").mkdir(parents=True, exist_ok=True)
    ids = sorted(payloads, key=lambda e: _parse(e)[1:])
    index = {
        "elections": [
            {"id": e, "type": _parse(e)[0], "year": _parse(e)[1], "round": _parse(e)[2], "label": _label(e)}
            for e in ids
        ]
    }
    classification = {
        "families": [
            {"id": f.id, "label": f.label, "position": f.position, "color": f.color} for f in families
        ],
        "lists": {
            f"{e}.{k}": {"label": m.label, "family": m.family}
            for e in ids
            for k, m in mappings[e].items()
        },
    }
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    (out / "classification.json").write_text(json.dumps(classification, ensure_ascii=False), encoding="utf-8")
    names_path = out / "names.json"
    existing = json.loads(names_path.read_text(encoding="utf-8")) if names_path.exists() else {}
    names_path.write_text(json.dumps({**existing, **names}, ensure_ascii=False), encoding="utf-8")
    for e in ids:
        territories = {
            tid: {**r, "voix": {f"{e}.{k}": v for k, v in r["voix"].items()}}
            for tid, r in payloads[e].items()
        }
        (out / "elections" / f"{e}.json").write_text(
            json.dumps({"id": e, "territories": territories}, ensure_ascii=False), encoding="utf-8"
        )
