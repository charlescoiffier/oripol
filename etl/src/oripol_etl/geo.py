from __future__ import annotations

import polars as pl


def build_geo(communes: pl.DataFrame, comer: pl.DataFrame, election_codes: list[str]) -> pl.DataFrame:
    """Référentiel code commune -> (département, région).

    - communes du COG (France métropolitaine + DOM) ;
    - collectivités d'outre-mer : chacune est à la fois son département et sa région ;
    - Français établis hors de France (codes ZZ…) : département fictif « ZZ », sans région.
    """
    base = communes.select(pl.col("com").alias("code"), "dep", "reg")
    outre_mer = comer.select(
        pl.col("com_comer").alias("code"), pl.col("comer").alias("dep"), pl.col("comer").alias("reg")
    )
    abroad = pl.DataFrame(
        {"code": sorted({c for c in election_codes if c.startswith("ZZ")})},
        schema={"code": pl.String},
    ).with_columns(pl.lit("ZZ").alias("dep"), pl.lit(None, dtype=pl.String).alias("reg"))
    known = set(base["code"]) | set(outre_mer["code"]) | set(abroad["code"])
    collectivites = set(comer["comer"])
    # codes qui désignent une collectivité entière (ex. 98601 pour Wallis-et-Futuna)
    whole = sorted(c for c in election_codes if c not in known and c[:3] in collectivites)
    whole_df = pl.DataFrame({"code": whole}, schema={"code": pl.String}).with_columns(
        pl.col("code").str.slice(0, 3).alias("dep"), pl.col("code").str.slice(0, 3).alias("reg")
    )
    return pl.concat([base, outre_mer, abroad, whole_df]).unique(subset="code", keep="first")
