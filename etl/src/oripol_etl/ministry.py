from __future__ import annotations

import re
from dataclasses import dataclass

import polars as pl

from .cog import CommuneResolver
from .families import normalize_key


@dataclass(frozen=True)
class ColumnMap:
    election_id: str
    bureau_id: str
    commune_code: pl.Expr
    inscrits: str
    votants: str
    blancs: str
    nuls: str
    exprimes: str
    cand_election_id: str
    cand_bureau_id: str
    cand_name: str
    cand_votes: str


def election_id_from_source(source_id: str) -> str | None:
    m = re.fullmatch(r"(\d{4})_pres_t1", source_id)
    return f"pres-{m.group(1)}-1" if m else None


def to_commune_tables(
    general: pl.DataFrame,
    candidates: pl.DataFrame,
    cm: ColumnMap,
    resolver: CommuneResolver,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    sources = general[cm.election_id].unique().to_list()
    id_map = {s: e for s in sources if (e := election_id_from_source(str(s)))}

    g = general.filter(pl.col(cm.election_id).is_in(list(id_map))).select(
        pl.col(cm.election_id).replace(id_map).alias("election_id"),
        pl.col(cm.bureau_id).alias("bureau"),
        cm.commune_code.cast(pl.String).alias("raw_code"),
        *[pl.col(getattr(cm, c)).alias(c) for c in ("inscrits", "votants", "blancs", "nuls", "exprimes")],
    )
    code_map = {c: resolver.resolve(c) for c in g["raw_code"].unique().to_list()}
    g = g.with_columns(pl.col("raw_code").replace(code_map).alias("code"))

    participation = g.group_by(["election_id", "code"]).agg(
        *[pl.col(c).sum() for c in ("inscrits", "votants", "blancs", "nuls", "exprimes")]
    )

    c = candidates.filter(pl.col(cm.cand_election_id).is_in(list(id_map))).select(
        pl.col(cm.cand_election_id).replace(id_map).alias("election_id"),
        pl.col(cm.cand_bureau_id).alias("bureau"),
        pl.col(cm.cand_name).alias("name"),
        pl.col(cm.cand_votes).alias("voix"),
    )
    names = {n: normalize_key(str(n)) for n in c["name"].unique().to_list()}
    c = c.with_columns(pl.col("name").replace(names).alias("list_key"))
    joined = c.join(g.select("election_id", "bureau", "code"), on=["election_id", "bureau"], how="inner")
    votes = joined.group_by(["election_id", "code", "list_key"]).agg(pl.col("voix").sum())
    return participation, votes
