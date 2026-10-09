from pathlib import Path

from oripol_etl.families import load_families, load_list_mappings, normalize_key

MAPPING = Path(__file__).resolve().parents[1] / "mappings" / "presidentielle.yaml"


def test_normalize_key_strips_accents_hyphens_and_case():
    assert normalize_key("Mélenchon") == "MELENCHON"
    assert normalize_key("Dupont-Aignan") == "DUPONT AIGNAN"
    assert normalize_key("  le  pen ") == "LE PEN"


def test_real_mapping_is_consistent():
    families = {f.id for f in load_families(MAPPING)}
    assert families == {
        "extreme_gauche", "gauche", "centre", "droite", "extreme_droite", "divers", "regionaliste"
    }
    mappings = load_list_mappings(MAPPING)
    assert set(mappings) == {"pres-2002-1", "pres-2007-1", "pres-2012-1", "pres-2017-1", "pres-2022-1"}
    for election, lists in mappings.items():
        for key, m in lists.items():
            assert m.family in families, (election, key)
            assert key == normalize_key(key)


def test_known_candidates_counts():
    mappings = load_list_mappings(MAPPING)
    assert len(mappings["pres-2002-1"]) == 16
    assert len(mappings["pres-2007-1"]) == 12
    assert len(mappings["pres-2012-1"]) == 10
    assert len(mappings["pres-2017-1"]) == 11
    assert len(mappings["pres-2022-1"]) == 12


def test_eelv_candidates_are_left():
    m = load_list_mappings(MAPPING)
    assert m["pres-2022-1"]["JADOT"].family == "gauche"
    assert m["pres-2012-1"]["JOLY"].family == "gauche"
