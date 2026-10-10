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


MAX_PEOPLE = 3  # au-delà, une commune n'affiche pas de noms pour une nuance


def build_names(election_id: str, names: pl.DataFrame, geo: pl.DataFrame) -> dict[str, dict[str, str]]:
    """Nom du candidat ou de la tête de liste par territoire et par nuance.

    Une commune liste ses personnes ; un département, une région ou le pays n'a de nom que s'il n'y en a qu'un seul
    en dessous (par exemple la tête de liste régionale d'une nuance dans toute sa région)."""
    n = names.filter(pl.col("election_id") == election_id).join(geo, on="code", how="inner")
    out: dict[str, dict[str, str]] = {}
    com = n.filter(pl.col("dep") != "ZZ")
    for code, key, people in com.group_by(["code", "list_key"]).agg(pl.col("person").sort().unique()).iter_rows():
        if len(people) <= MAX_PEOPLE:
            out.setdefault(f"COM-{code}", {})[key] = " / ".join(people)
    for prefix, col, frame in (("DEP", "dep", n), ("REG", "reg", n.filter(pl.col("reg").is_not_null())), ("FR", None, n)):
        key_col = pl.col(col) if col else pl.lit("")
        grouped = frame.group_by([key_col.alias("k"), "list_key"]).agg(
            pl.col("person").n_unique().alias("n"), pl.col("person").first().alias("person")
        )
        for k, key, count, person in grouped.iter_rows():
            if count == 1:
                out.setdefault(f"{prefix}-{k}" if col else "FR", {})[key] = person
    return out
