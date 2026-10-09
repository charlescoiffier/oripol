from __future__ import annotations

import polars as pl

from . import config as c
from .aggregate import build_payload
from .cog import build_resolver
from .export import write_site_data
from .families import load_families, load_list_mappings
from .ministry import to_commune_tables
from .targets import chefs_lieux, population_max, select_targets
from .validate import validate


def _csv(path):
    df = pl.read_csv(path, infer_schema=False)  # tout en texte : codes Corse (2A001) et zéros initiaux
    return df.rename({col: col.lower() for col in df.columns})


def _table(path):
    return pl.read_parquet(path) if str(path).endswith(".parquet") else pl.read_csv(path, infer_schema=False)


def run() -> None:
    communes = _csv(c.COG_COMMUNES).filter(pl.col("typecom") == "COM")
    geo = communes.select(pl.col("com").alias("code"), "dep", "reg")
    current = set(geo["code"].to_list())
    resolver = build_resolver(_csv(c.COG_MOUVEMENTS), current)

    pop = pl.read_excel(c.POP_FILE, sheet_name=c.POP_SHEET, read_options={"header_row": c.POP_HEADER_ROW})
    lieux = chefs_lieux(_csv(c.COG_DEPARTEMENTS), _csv(c.COG_ARRONDISSEMENTS))
    targets_df = select_targets(population_max(pop, c.POP_ID_COL, c.POP_EXCLUDE), lieux, resolver)
    targets = [t for t in targets_df["code"].to_list() if resolver.is_current(t)]

    families = load_families(c.MAPPING)
    mappings = load_list_mappings(c.MAPPING)
    participation, votes = to_commune_tables(_table(c.GENERAL_FILE), _table(c.CANDIDATES_FILE), c.COLUMNS, resolver)
    participation = participation.join(geo.select("code"), on="code", how="inner")
    votes = votes.join(geo.select("code"), on="code", how="inner")

    validate(participation, votes, mappings)  # lève avant toute écriture
    payloads = {
        e: build_payload(e, participation, votes, geo, targets)
        for e in sorted(participation["election_id"].unique().to_list())
    }
    write_site_data(c.OUT, families, mappings, payloads, names={})
    (c.OUT / "targets.txt").write_text("\n".join(targets), encoding="utf-8")
    print(f"{len(payloads)} élections, {len(targets)} communes cibles → {c.OUT}")


if __name__ == "__main__":
    run()
