from __future__ import annotations

import polars as pl

from . import config as c
from .aggregate import build_names, build_payload
from .cog import build_resolver
from .export import write_parents, write_site_data
from .families import load_all_mappings, load_families
from .geo import build_geo
from .ministry import reconcile_unclassified, to_commune_names, to_commune_tables
from .validate import validate, validate_coverage


def _csv(path):
    df = pl.read_csv(path, infer_schema=False)  # tout en texte : codes Corse (2A001) et zéros initiaux
    return df.rename({col: col.lower() for col in df.columns})


def _table(path):
    return pl.read_parquet(path) if str(path).endswith(".parquet") else pl.read_csv(path, infer_schema=False)


def run() -> None:
    communes = _csv(c.COG_COMMUNES).filter(pl.col("typecom") == "COM")
    comer_communes = _csv(c.COG_COMER_COMMUNES)
    current = set(communes["com"].to_list()) | set(comer_communes["com_comer"].to_list())
    resolver = build_resolver(_csv(c.COG_MOUVEMENTS), current)

    families = load_families(c.FAMILIES)
    mappings = load_all_mappings(c.MAPPINGS, {f.id for f in families})
    general, candidates = _table(c.GENERAL_FILE), _table(c.CANDIDATES_FILE)
    participation, votes = to_commune_tables(general, candidates, c.COLUMNS, resolver)
    person_rows = to_commune_names(general, candidates, c.COLUMNS, resolver)
    votes = reconcile_unclassified(participation, votes, types={"muni"})
    geo = build_geo(communes, comer_communes, participation["code"].unique().to_list())

    validate_coverage(participation, set(geo["code"].to_list()))  # lève si de vraies communes ne se résolvent pas
    participation = participation.join(geo.select("code"), on="code", how="inner")
    votes = votes.join(geo.select("code"), on="code", how="inner")

    validate(participation, votes, mappings)  # lève avant toute écriture
    payloads = {
        e: build_payload(e, participation, votes, geo)
        for e in sorted(participation["election_id"].unique().to_list())
    }
    people = {e: build_names(e, person_rows, geo) for e in payloads}
    comer = _csv(c.COG_COMER)
    names = {"DEP-ZZ": "Français établis hors de France"}
    for code, label in zip(comer["comer"], comer["libelle"]):
        names[f"DEP-{code}"] = label
        names[f"REG-{code}"] = label
    write_site_data(c.OUT, families, mappings, payloads, names=names, people=people)
    write_parents(c.OUT, geo)
    print(f"{len(payloads)} élections, {geo.height} communes → {c.OUT}")


if __name__ == "__main__":
    run()
