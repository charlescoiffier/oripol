from pathlib import Path

import pytest

from oripol_etl.families import load_all_mappings, load_families, load_list_mappings, normalize_key

MAPPINGS = Path(__file__).resolve().parents[1] / "mappings"
FAMILY_IDS = {"extreme_gauche", "gauche", "centre", "droite", "extreme_droite", "divers", "regionaliste"}


def real_mappings():
    families = {f.id for f in load_families(MAPPINGS / "families.yaml")}
    return load_all_mappings([MAPPINGS / "presidentielle.yaml", MAPPINGS / "legislatives.yaml"], families)


def test_normalize_key_strips_accents_hyphens_and_case():
    assert normalize_key("Mélenchon") == "MELENCHON"
    assert normalize_key("Dupont-Aignan") == "DUPONT AIGNAN"
    assert normalize_key("  le  pen ") == "LE PEN"


def test_families_file_is_the_expected_set():
    assert {f.id for f in load_families(MAPPINGS / "families.yaml")} == FAMILY_IDS


def test_real_mappings_cover_presidential_and_legislative_elections():
    m = real_mappings()
    pres = {f"pres-{y}-{r}" for y in (2002, 2007, 2012, 2017, 2022) for r in (1, 2)}
    legi = {f"legi-{y}-{r}" for y in (2002, 2007, 2012, 2017, 2022, 2024) for r in (1, 2)}
    assert set(m) == pres | legi
    for election, lists in m.items():
        for key, mapping in lists.items():
            assert mapping.family in FAMILY_IDS, (election, key)
            assert key == normalize_key(key)


def test_known_candidates_counts():
    m = real_mappings()
    assert [len(m[f"pres-{y}-1"]) for y in (2002, 2007, 2012, 2017, 2022)] == [16, 12, 10, 11, 12]
    assert all(len(m[f"pres-{y}-2"]) == 2 for y in (2002, 2007, 2012, 2017, 2022))


def test_eelv_candidates_are_left():
    m = real_mappings()
    assert m["pres-2022-1"]["JADOT"].family == "gauche"
    assert m["pres-2012-1"]["JOLY"].family == "gauche"


def test_legislative_nuances_are_shared_across_elections():
    m = real_mappings()
    assert m["legi-2002-1"]["UMP"].family == "droite"
    assert m["legi-2024-2"]["RN"].family == "extreme_droite"
    assert m["legi-2022-1"]["NUP"].family == "gauche"
    assert m["legi-2002-1"]["UMP"] == m["legi-2012-2"]["UMP"]


def test_unknown_family_is_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("elections:\n  pres-2002-1:\n    - {key: X, label: X, family: nope}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="famille inconnue"):
        load_list_mappings(bad, FAMILY_IDS)


def test_same_election_defined_twice_is_rejected(tmp_path):
    a = tmp_path / "a.yaml"
    a.write_text("elections:\n  pres-2002-1:\n    - {key: X, label: X, family: gauche}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="deux fois"):
        load_all_mappings([a, a], FAMILY_IDS)
