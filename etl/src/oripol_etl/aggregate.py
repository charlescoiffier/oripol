from __future__ import annotations

import polars as pl

SUM_COLS = ["inscrits", "votants", "blancs", "nuls", "exprimes"]
# (préfixe, colonne de regroupement, filtre éventuel)
LEVELS = [("COM", "code"), ("DEP", "dep"), ("REG", "reg"), ("FR", None)]


def build_payload(
    election_id: str,
    participation: pl.DataFrame,
    votes: pl.DataFrame,
    geo: pl.DataFrame,
) -> dict[str, dict]:
    part = participation.filter(pl.col("election_id") == election_id).join(geo, on="code", how="inner")
    vote = votes.filter(pl.col("election_id") == election_id).join(geo, on="code", how="inner")
    out: dict[str, dict] = {}
    for prefix, col in LEVELS:
        p, v = part, vote
        if prefix == "COM":  # les bureaux consulaires (dép. ZZ) n'ont pas de commune
            p, v = p.filter(pl.col("dep") != "ZZ"), v.filter(pl.col("dep") != "ZZ")
        elif prefix == "REG":
            p, v = p.filter(pl.col("reg").is_not_null()), v.filter(pl.col("reg").is_not_null())
        key = pl.col(col) if col else pl.lit("")

        def tid(k: str) -> str:
            return f"{prefix}-{k}" if col else "FR"

        for row in p.group_by(key.alias("k")).agg([pl.col(c).sum() for c in SUM_COLS]).iter_rows(named=True):
            out[tid(row["k"])] = {**{c: row[c] for c in SUM_COLS}, "voix": {}, "precision": "commune"}
        for row in v.group_by([key.alias("k"), "list_key"]).agg(pl.col("voix").sum()).iter_rows(named=True):
            out[tid(row["k"])]["voix"][row["list_key"]] = row["voix"]
    return out


def build_names(election_id: str, names: pl.DataFrame, geo: pl.DataFrame) -> dict[str, dict[str, str]]:
    """Nom du candidat ou de la tête de liste par territoire agrégé et par nuance.

    Un département, une région ou le pays n'a de nom que s'il n'y en a qu'un seul en dessous (par exemple la tête de
    liste régionale d'une nuance dans toute sa région). Un nom identique à celui du pays n'est pas répété : le site
    retombe sur le pays. Les communes ont leurs listes détaillées (voir `build_lists`)."""
    n = names.filter(pl.col("election_id") == election_id).join(geo, on="code", how="inner")
    out: dict[str, dict[str, str]] = {}
    for prefix, col, frame in (("DEP", "dep", n), ("REG", "reg", n.filter(pl.col("reg").is_not_null())), ("FR", None, n)):
        key_col = pl.col(col) if col else pl.lit("")
        grouped = frame.group_by([key_col.alias("k"), "list_key"]).agg(
            pl.col("person").n_unique().alias("n"), pl.col("person").first().alias("person")
        )
        for k, key, count, person in grouped.iter_rows():
            if count == 1:
                out.setdefault(f"{prefix}-{k}" if col else "FR", {})[key] = person
    country = out.get("FR", {})
    for tid in [t for t in out if t != "FR"]:
        out[tid] = {k: p for k, p in out[tid].items() if country.get(k) != p}
        if not out[tid]:
            del out[tid]
    return out


def build_lists(election_id: str, names: pl.DataFrame, geo: pl.DataFrame) -> dict[str, list[tuple[str, str, int]]]:
    """Listes ou candidats de chaque commune, une à une : (nuance, nom, voix), de la plus votée à la moins votée."""
    n = (
        names.filter(pl.col("election_id") == election_id)
        .join(geo, on="code", how="inner")
        .filter(pl.col("dep") != "ZZ")
        .sort(["code", "voix", "person"], descending=[False, True, False])
    )
    out: dict[str, list[tuple[str, str, int]]] = {}
    for code, key, person, voix in n.select("code", "list_key", "person", "voix").iter_rows():
        out.setdefault(f"COM-{code}", []).append((key, person, voix))
    return out
