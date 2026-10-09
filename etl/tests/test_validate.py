import polars as pl
import pytest

from oripol_etl.families import ListMapping
from oripol_etl.validate import validate

M = {"e": {"X": ListMapping("X", "X", "gauche"), "Y": ListMapping("Y", "Y", "droite")}}


def tables(voix_y=28, key="Y"):
    part = pl.DataFrame({"election_id": ["e"], "code": ["A"], "exprimes": [78]})
    votes = pl.DataFrame({"election_id": ["e"] * 2, "code": ["A", "A"], "list_key": ["X", key], "voix": [50, voix_y]})
    return part, votes


def test_valid_tables_pass():
    validate(*tables(), M)


def test_sum_mismatch_raises():
    with pytest.raises(ValueError, match="somme des voix"):
        validate(*tables(voix_y=29), M)


def test_unmapped_list_raises():
    with pytest.raises(ValueError, match="sans famille"):
        validate(*tables(key="GHOST"), M)
