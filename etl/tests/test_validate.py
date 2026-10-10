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
        validate(*tables(voix_y=60), M)


def test_tiny_source_discrepancy_is_tolerated():
    # le fichier officiel contient quelques communes à 1-2 voix d'écart (recomptes) : on ne bloque pas
    validate(*tables(voix_y=29), M)


def test_unmapped_list_raises():
    with pytest.raises(ValueError, match="sans famille"):
        validate(*tables(key="GHOST"), M)


def coverage_tables(unresolved_exprimes):
    part = pl.DataFrame(
        {
            "election_id": ["e"] * 2,
            "code": ["A", "B1"],
            "exprimes": [1_000_000, unresolved_exprimes],
        }
    )
    return part, {"A"}


def test_coverage_passes_when_everything_resolves():
    from oripol_etl.validate import validate_coverage

    part, current = coverage_tables(0)
    validate_coverage(part.filter(pl.col("code") != "B1"), current)


def test_coverage_tolerates_a_tiny_unresolved_share():
    from oripol_etl.validate import validate_coverage

    part, current = coverage_tables(300)  # 0,03 % des exprimés
    validate_coverage(part, current)


def test_coverage_raises_when_a_real_commune_is_unresolved():
    from oripol_etl.validate import validate_coverage

    part, current = coverage_tables(50_000)
    with pytest.raises(ValueError, match="codes commune non résolus"):
        validate_coverage(part, current)
