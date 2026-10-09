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


# Codes légitimement absents du COG des communes : Français établis hors de France (Z…),
# Polynésie/Nouvelle-Calédonie/Wallis (98…), Saint-Pierre-et-Miquelon (975), Saint-Barthélemy
# et Saint-Martin (977, 978 et leurs anciens codes 97123, 97127).
IGNORABLE_PREFIXES = ("Z", "98", "975", "977", "978", "97123", "97127")


def validate_coverage(
    participation: pl.DataFrame,
    current_codes: set[str],
    max_unresolved_share: float = 0.0005,
) -> None:
    """Échoue si des communes réelles non résolues pèsent plus de 0,05 % des exprimés d'une élection."""
    total = participation.group_by("election_id").agg(pl.col("exprimes").sum().alias("total"))
    unresolved = (
        participation.filter(~pl.col("code").is_in(list(current_codes)))
        .filter(~pl.col("code").str.starts_with(IGNORABLE_PREFIXES[0]))
        .filter(
            ~pl.any_horizontal([pl.col("code").str.starts_with(p) for p in IGNORABLE_PREFIXES[1:]])
        )
        .group_by("election_id")
        .agg(pl.col("exprimes").sum().alias("lost"), pl.col("code").unique().sort().alias("codes"))
        .join(total, on="election_id")
        .filter(pl.col("lost") / pl.col("total") > max_unresolved_share)
    )
    if unresolved.height:
        raise ValueError(f"codes commune non résolus (hors exclusions connues):\n{unresolved}")
