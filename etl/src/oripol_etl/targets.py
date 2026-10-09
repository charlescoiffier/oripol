from __future__ import annotations

import polars as pl

from .cog import CommuneResolver


def population_max(df: pl.DataFrame, id_col: str, exclude: list[str]) -> pl.DataFrame:
    skip = {id_col, *exclude}
    numeric = [c for c in df.columns if c not in skip and df[c].dtype.is_numeric()]
    return df.select(
        pl.col(id_col).alias("code"),
        pl.max_horizontal([pl.col(c) for c in numeric]).alias("max_population"),
    )


def chefs_lieux(departements: pl.DataFrame, arrondissements: pl.DataFrame) -> pl.DataFrame:
    prefectures = departements.select(pl.col("cheflieu").alias("code")).unique()
    prefectures = prefectures.with_columns(pl.lit("prefecture").alias("motif"))
    sous = (
        arrondissements.select(pl.col("cheflieu").alias("code"))
        .unique()
        .join(prefectures.select("code"), on="code", how="anti")
        .with_columns(pl.lit("sous_prefecture").alias("motif"))
    )
    return pl.concat([prefectures, sous])


def select_targets(
    max_pop: pl.DataFrame,
    lieux: pl.DataFrame,
    resolver: CommuneResolver,
    threshold: int = 30000,
) -> pl.DataFrame:
    rows: list[tuple[str, str]] = []
    for code, pop in zip(max_pop["code"], max_pop["max_population"]):
        if pop is not None and pop >= threshold:
            rows.append((resolver.resolve(code), "seuil_30000"))
    for code, motif in zip(lieux["code"], lieux["motif"]):
        rows.append((resolver.resolve(code), motif))
    df = pl.DataFrame(rows, schema={"code": pl.String, "motif": pl.String}, orient="row")
    return (
        df.group_by("code")
        .agg(pl.col("motif").unique().sort().str.join(",").alias("motifs"))
        .sort("code")
    )
