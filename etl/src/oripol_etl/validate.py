from __future__ import annotations

import polars as pl

from .families import ListMapping


def validate(
    participation: pl.DataFrame,
    votes: pl.DataFrame,
    mappings: dict[str, dict[str, ListMapping]],
    tolerance_abs: int = 3,
    tolerance_rel: float = 0.005,
    max_election_deviation: float = 0.0005,
) -> None:
    """Contrôles bloquants.

    - un écart de quelques voix (recomptes dans le fichier officiel) est toléré ;
    - des communes isolées défectueuses sont signalées, sans bloquer, tant que leurs écarts pèsent moins de
      `max_election_deviation` des exprimés du scrutin ; au-delà, le traitement échoue."""
    sums = votes.group_by(["election_id", "code"]).agg(pl.col("voix").sum().alias("sum_voix"))
    bad = (
        participation.join(sums, on=["election_id", "code"], how="left")
        .with_columns(pl.col("sum_voix").fill_null(0))
        .filter(
            (pl.col("sum_voix") - pl.col("exprimes")).abs()
            > pl.max_horizontal(pl.lit(tolerance_abs), (pl.col("exprimes") * tolerance_rel).ceil())
        )
    )
    if bad.height:
        totals = participation.group_by("election_id").agg(pl.col("exprimes").sum().alias("total"))
        weight = (
            bad.with_columns((pl.col("sum_voix") - pl.col("exprimes")).abs().alias("gap"))
            .group_by("election_id")
            .agg(pl.col("gap").sum())
            .join(totals, on="election_id")
            .with_columns((pl.col("gap") / pl.col("total")).alias("share"))
        )
        if weight.filter(pl.col("share") > max_election_deviation).height:
            raise ValueError(f"somme des voix ≠ exprimés pour {bad.height} commune(s):\n{bad.head(10)}")
        print(f"avertissement : {bad.height} commune(s) à somme des voix ≠ exprimés (source) :\n{bad.head(10)}")

    missing = []
    for election_id, keys in votes.group_by("election_id").agg(pl.col("list_key").unique()).iter_rows():
        for k in keys:
            if k not in mappings.get(election_id, {}):
                missing.append(f"{election_id}.{k}")
    if missing:
        raise ValueError(f"candidats sans famille: {sorted(missing)}")


def validate_coverage(
    participation: pl.DataFrame,
    current_codes: set[str],
    max_unresolved_share: float = 0.0005,
) -> None:
    """Échoue si des codes commune non résolus pèsent plus de 0,05 % des exprimés d'une élection."""
    total = participation.group_by("election_id").agg(pl.col("exprimes").sum().alias("total"))
    unresolved = (
        participation.filter(~pl.col("code").is_in(list(current_codes)))
        .group_by("election_id")
        .agg(pl.col("exprimes").sum().alias("lost"), pl.col("code").unique().sort().alias("codes"))
        .join(total, on="election_id")
        .filter(pl.col("lost") / pl.col("total") > max_unresolved_share)
    )
    if unresolved.height:
        raise ValueError(f"codes commune non résolus:\n{unresolved}")
