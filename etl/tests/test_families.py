from pathlib import Path

import pytest

from oripol_etl.families import load_all_mappings, load_families, load_list_mappings, normalize_key

MAPPINGS = Path(__file__).resolve().parents[1] / "mappings"
FAMILY_IDS = {"extreme_gauche", "gauche", "centre", "droite", "extreme_droite", "divers", "regionaliste", "non_classe"}


def real_mappings():
    families = {f.id for f in load_families(MAPPINGS / "families.yaml")}
    return load_all_mappings(
        [MAPPINGS / "presidentielle.yaml", MAPPINGS / "nuances.yaml", MAPPINGS / "europeennes-2019.yaml"], families
    )


def test_normalize_key_strips_accents_hyphens_and_case():
    assert normalize_key("Mélenchon") == "MELENCHON"
    assert normalize_key("Dupont-Aignan") == "DUPONT AIGNAN"
    assert normalize_key("  le  pen ") == "LE PEN"


def test_families_file_is_the_expected_set():
    assert {f.id for f in load_families(MAPPINGS / "families.yaml")} == FAMILY_IDS


def test_real_mappings_cover_all_supported_elections():
    m = real_mappings()
    pres = {f"pres-{y}-{r}" for y in (2002, 2007, 2012, 2017, 2022) for r in (1, 2)}
    legi = {f"legi-{y}-{r}" for y in (2002, 2007, 2012, 2017, 2022, 2024) for r in (1, 2)}
    euro = {f"euro-{y}-1" for y in (1999, 2004, 2009, 2014, 2019, 2024)}
    regi = {f"regi-{y}-{r}" for y in (2004, 2010, 2015, 2021) for r in (1, 2)}
    dpmt = {f"dpmt-{y}-{r}" for y in (2015, 2021) for r in (1, 2)}
    cant = {f"cant-{y}-{r}" for y in (2001, 2004, 2008, 2011) for r in (1, 2)}
    muni = {f"muni-{y}-{r}" for y in (2008, 2014, 2020, 2026) for r in (1, 2)}
    assert set(m) == pres | legi | euro | regi | dpmt | cant | muni
    for election, lists in m.items():
        for key, mapping in lists.items():
            assert mapping.family in FAMILY_IDS, (election, key)
            assert key == key.strip().upper()


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


def test_lfi_is_extreme_left_in_2026_municipales_only():
    m = real_mappings()
    assert m["muni-2026-1"]["LFI"].family == "extreme_gauche"
    assert m["muni-2026-2"]["LFI"].family == "extreme_gauche"
    assert m["muni-2020-1"]["LFI"].family == "gauche"
    assert m["legi-2024-1"]["LFI"].family == "gauche"


def test_override_with_unknown_code_or_family_is_rejected(tmp_path):
    base = "applies_to: [muni-2026-1]\nnuances:\n  LFI: {label: x, family: gauche}\n"
    bad_code = tmp_path / "a.yaml"
    bad_code.write_text(base + "overrides:\n  muni-2026-1: {XYZ: gauche}\n")
    with pytest.raises(ValueError):
        load_list_mappings(bad_code, FAMILY_IDS)
    bad_family = tmp_path / "b.yaml"
    bad_family.write_text(base + "overrides:\n  muni-2026-1: {LFI: nope}\n")
    with pytest.raises(ValueError):
        load_list_mappings(bad_family, FAMILY_IDS)


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


def test_european_2019_lists_are_mapped_by_name():
    m = real_mappings()
    assert len(m["euro-2019-1"]) == 34
    assert m["euro-2019-1"]["PRENEZ LE POUVOIR"].family == "extreme_droite"
    assert m["euro-2019-1"]["UNION DROITE CENTRE"].family == "droite"


def test_nuance_codes_with_a_hyphen_keep_it():
    m = real_mappings()
    assert "M-NC" in m["cant-2008-1"]  # code de nuance : pas de normalisation de nom
    assert m["cant-2008-1"]["M-NC"].family == "centre"


def test_non_classe_family_is_outside_the_political_base():
    families = {f.id: f for f in load_families(MAPPINGS / "families.yaml")}
    assert families["non_classe"].in_base is False
    assert families["gauche"].in_base is True
    assert real_mappings()["muni-2020-1"]["NC"].family == "non_classe"
