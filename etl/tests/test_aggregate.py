import polars as pl

from oripol_etl.aggregate import build_payload

PART = pl.DataFrame(
    {
        "election_id": ["e"] * 4,
        "code": ["A1", "A2", "B1", "ZZ1"],
        "inscrits": [100, 100, 100, 10],
        "votants": [80, 80, 80, 5],
        "blancs": [1, 1, 1, 0],
        "nuls": [1, 1, 1, 0],
        "exprimes": [78, 78, 78, 5],
    }
)
VOTES = pl.DataFrame(
    {
        "election_id": ["e"] * 7,
        "code": ["A1", "A1", "A2", "A2", "B1", "B1", "ZZ1"],
        "list_key": ["X", "Y", "X", "Y", "X", "Y", "X"],
        "voix": [50, 28, 40, 38, 10, 68, 5],
    }
)
GEO = pl.DataFrame(
    {"code": ["A1", "A2", "B1", "ZZ1"], "dep": ["01", "01", "02", "ZZ"], "reg": ["R1", "R1", "R1", None]}
)


def test_all_communes_and_every_level_without_targets():
    p = build_payload("e", PART, VOTES, GEO)
    assert set(p) == {"COM-A1", "COM-A2", "COM-B1", "DEP-01", "DEP-02", "DEP-ZZ", "REG-R1", "FR"}
    assert p["DEP-01"]["exprimes"] == 156
    assert p["DEP-01"]["voix"] == {"X": 90, "Y": 66}
    assert p["COM-A1"]["voix"] == {"X": 50, "Y": 28}


def test_abroad_counts_in_france_but_has_no_commune_or_region():
    p = build_payload("e", PART, VOTES, GEO)
    assert p["FR"]["exprimes"] == 239  # 234 + 5 Français de l'étranger
    assert p["DEP-ZZ"]["voix"] == {"X": 5}
    assert not any(k.startswith("COM-ZZ") for k in p)
    assert p["REG-R1"]["exprimes"] == 234  # le ZZ (sans région) n'est pas compté dans R1
