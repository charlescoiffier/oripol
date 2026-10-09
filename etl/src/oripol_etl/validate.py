from __future__ import annotations

import polars as pl

from .families import ListMapping


def validate(
    participation: pl.DataFrame,
    votes: pl.DataFrame,
    mappings: dict[str, dict[str, ListMapping]],
) -> None:
    sums = votes.group_by(["election_id", "code"]).agg(pl.col("voix").sum().alias("sum_voix"))
    bad = (
        participation.join(sums, on=["election_id", "code"], how="left")
        .with_columns(pl.col("sum_voix").fill_null(0))
        .filter(pl.col("sum_voix") != pl.col("exprimes"))
    )
    if bad.height:
        raise ValueError(f"somme des voix ≠ exprimés pour {bad.height} commune(s):\n{bad.head(10)}")

    missing = []
    for election_id, keys in votes.group_by("election_id").agg(pl.col("list_key").unique()).iter_rows():
        for k in keys:
            if k not in mappings.get(election_id, {}):
                missing.append(f"{election_id}.{k}")
    if missing:
        raise ValueError(f"candidats sans famille: {sorted(missing)}")
