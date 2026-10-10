from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from .families import Family, ListMapping

LABELS = {
    "pres": "Présidentielle",
    "legi": "Législatives",
    "euro": "Européennes",
    "regi": "Régionales",
    "dpmt": "Départementales",
    "cant": "Cantonales",
    "muni": "Municipales",
}


def _parse(election_id: str) -> tuple[str, int, int]:
    kind, year, rnd = election_id.split("-")
    return kind, int(year), int(rnd)


def _label(election_id: str) -> str:
    kind, year, rnd = _parse(election_id)
    return f"{LABELS[kind]} {year} – {'1er' if rnd == 1 else '2d'} tour"


def pack_people(
    by_territory: dict[str, dict[str, str]],
    commune_lists: dict[str, list[tuple[str, str, int]]] | None = None,
) -> dict:
    """Format compact : table de noms dédupliquée, `t` (territoire → `[nuance, indice du nom, …]`) pour les noms
    uniques des territoires agrégés, `c` (commune → `[nuance, indice du nom, voix, …]`) pour les listes une à une."""
    table: dict[str, int] = {}
    packed: dict[str, list] = {}
    for tid, by_key in by_territory.items():
        flat: list = []
        for key, person in by_key.items():
            flat += [key, table.setdefault(person, len(table))]
        packed[tid] = flat
    lists: dict[str, list] = {}
    for tid, entries in (commune_lists or {}).items():
        flat = []
        for key, person, voix in entries:
            flat += [key, table.setdefault(person, len(table)), voix]
        lists[tid] = flat
    return {"names": list(table), "t": packed, "c": lists}


def write_site_data(
    out: Path,
    families: list[Family],
    mappings: dict[str, dict[str, ListMapping]],
    payloads: dict[str, dict],
    names: dict[str, str],
    people: dict[str, dict[str, dict[str, str]]] | None = None,
    commune_lists: dict[str, dict[str, list[tuple[str, str, int]]]] | None = None,
) -> None:
    """`people` : par élection, territoire → nuance → nom du candidat ou de la tête de liste (fichiers à part)."""
    people = people or {}
    commune_lists = commune_lists or {}
    (out / "elections").mkdir(parents=True, exist_ok=True)
    ids = sorted(payloads, key=lambda e: _parse(e)[1:])
    index = {
        "elections": [
            {
                "id": e,
                "type": _parse(e)[0],
                "year": _parse(e)[1],
                "round": _parse(e)[2],
                "label": _label(e),
                **({"people": True} if people.get(e) or commune_lists.get(e) else {}),
            }
            for e in ids
        ]
    }
    classification = {
        "families": [
            {"id": f.id, "label": f.label, "position": f.position, "color": f.color, "inBase": f.in_base}
            for f in families
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
    (out / "people").mkdir(exist_ok=True)
    for e in sorted(set(people) | set(commune_lists)):
        if people.get(e) or commune_lists.get(e):
            (out / "people" / f"{e}.json").write_text(
                json.dumps(pack_people(people.get(e, {}), commune_lists.get(e)), ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
    for e in ids:
        keys = sorted({k for r in payloads[e].values() for k in r["voix"]})
        territories = {
            tid: [r[c] for c in ("inscrits", "votants", "blancs", "nuls", "exprimes")]
            + [r["voix"].get(k, 0) for k in keys]
            for tid, r in payloads[e].items()
        }
        # tout est à la précision « commune » : le champ est implicite côté site
        (out / "elections" / f"{e}.json").write_text(
            json.dumps(
                {"id": e, "lists": [f"{e}.{k}" for k in keys], "territories": territories},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )


def write_parents(out: Path, geo: pl.DataFrame) -> None:
    """Hiérarchie des territoires (id -> id du parent) : commune → département → région."""
    parents: dict[str, str] = {}
    for code, dep, reg in geo.select("code", "dep", "reg").iter_rows():
        if dep == "ZZ":  # Français établis hors de France : pas de commune ni de région
            continue
        parents[f"COM-{code}"] = f"DEP-{dep}"
        if reg is not None:
            parents[f"DEP-{dep}"] = f"REG-{reg}"
    (out / "parents.json").write_text(json.dumps(parents, separators=(",", ":")), encoding="utf-8")
