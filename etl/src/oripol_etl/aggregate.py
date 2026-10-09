from __future__ import annotations

import polars as pl

SUM_COLS = ["inscrits", "votants", "blancs", "nuls", "exprimes"]
LEVELS = [("COM", "code", True), ("DEP", "dep", False), ("REG", "reg", False), ("FR", None, False)]


def build_payload(
    election_id: str,
    participation: pl.DataFrame,
    votes: pl.DataFrame,
    geo: pl.DataFrame,
    targets: list[str],
) -> dict[str, dict]:
    part = participation.filter(pl.col("election_id") == election_id).join(geo, on="code", how="inner")
    vote = votes.filter(pl.col("election_id") == election_id).join(geo, on="code", how="inner")
    out: dict[str, dict] = {}
    for prefix, col, only_targets in LEVELS:
        p, v = part, vote
        if only_targets:
            p = p.filter(pl.col("code").is_in(targets))
            v = v.filter(pl.col("code").is_in(targets))
        key = pl.col(col) if col else pl.lit("")

        def tid(k: str) -> str:
            return f"{prefix}-{k}" if col else "FR"

        for row in p.group_by(key.alias("k")).agg([pl.col(c).sum() for c in SUM_COLS]).iter_rows(named=True):
            out[tid(row["k"])] = {**{c: row[c] for c in SUM_COLS}, "voix": {}, "precision": "commune"}
        for row in v.group_by([key.alias("k"), "list_key"]).agg(pl.col("voix").sum()).iter_rows(named=True):
            out[tid(row["k"])]["voix"][row["list_key"]] = row["voix"]
    return out
