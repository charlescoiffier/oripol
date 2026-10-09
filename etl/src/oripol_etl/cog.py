from __future__ import annotations

import polars as pl

ARRONDISSEMENTS_MUNICIPAUX: dict[str, str] = {
    **{f"751{n:02d}": "75056" for n in range(1, 21)},
    **{f"6938{n}": "69123" for n in range(1, 10)},
    **{f"132{n:02d}": "13055" for n in range(1, 17)},
}

# 31 fusion simple, 32 création de commune nouvelle, 33 fusion avec association,
# 34 fusion association → simple, 41 changement de département, 50 changement de code (fusion)
MERGE_MODS = {31, 32, 33, 34, 41, 50}


class CommuneResolver:
    def __init__(self, direct: dict[str, str], current: set[str]):
        self._direct = direct
        self._current = current

    def resolve(self, code: str) -> str:
        code = ARRONDISSEMENTS_MUNICIPAUX.get(code, code)
        seen: set[str] = set()
        while code in self._direct and code not in seen:
            seen.add(code)
            code = self._direct[code]
        return code

    def is_current(self, code: str) -> bool:
        return code in self._current


def build_resolver(mouvements: pl.DataFrame, current_codes: set[str]) -> CommuneResolver:
    df = mouvements.rename({c: c.lower() for c in mouvements.columns})
    df = df.filter(
        pl.col("mod").cast(pl.Int64).is_in(list(MERGE_MODS))
        & (pl.col("typecom_av") == "COM")
        & (pl.col("typecom_ap") == "COM")
        & (pl.col("com_av") != pl.col("com_ap"))
    ).sort("date_eff")
    direct: dict[str, str] = {}
    for old, new in zip(df["com_av"], df["com_ap"]):
        if old in current_codes:
            continue  # code réutilisé (commune rétablie) : ne jamais le remapper
        direct[old] = new
    return CommuneResolver(direct, set(current_codes))
