import polars as pl

from oripol_etl.aggregate import build_payload

PART = pl.DataFrame(
    {
        "election_id": ["e"] * 4,
        "code": ["A1", "A2", "B1", "ZZ"],
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
        "code": ["A1", "A1", "A2", "A2", "B1", "B1", "ZZ"],
        "list_key": ["X", "Y", "X", "Y", "X", "Y", "X"],
        "voix": [50, 28, 40, 38, 10, 68, 5],
    }
)
GEO = pl.DataFrame({"code": ["A1", "A2", "B1"], "dep": ["01", "01", "02"], "reg": ["R1", "R1", "R1"]})


def test_levels_and_targets():
    p = build_payload("e", PART, VOTES, GEO, targets=["A1"])
    assert set(p) == {"COM-A1", "DEP-01", "DEP-02", "REG-R1", "FR"}
    assert p["DEP-01"]["exprimes"] == 156
    assert p["DEP-01"]["voix"] == {"X": 90, "Y": 66}
    assert p["COM-A1"]["voix"] == {"X": 50, "Y": 28}
    assert p["FR"]["exprimes"] == 234  # ZZ (hors COG) ignoré
    assert p["FR"]["precision"] == "commune"
