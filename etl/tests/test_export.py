import json

from oripol_etl.export import write_site_data
from oripol_etl.families import Family, ListMapping


def test_writes_prefixed_list_ids_and_index(tmp_path):
    families = [Family("gauche", "Gauche", -1, "#f00")]
    mappings = {"pres-2022-1": {"X": ListMapping("X", "Candidat X", "gauche")}}
    payloads = {
        "pres-2022-1": {
            "FR": {"inscrits": 10, "votants": 8, "blancs": 1, "nuls": 1, "exprimes": 8, "voix": {"X": 8}, "precision": "commune"}
        }
    }
    write_site_data(tmp_path, families, mappings, payloads, names={"FR": "France"})
    idx = json.loads((tmp_path / "index.json").read_text())
    assert idx["elections"] == [{"id": "pres-2022-1", "type": "pres", "year": 2022, "round": 1, "label": "Présidentielle 2022 – 1er tour"}]
    cls = json.loads((tmp_path / "classification.json").read_text())
    assert cls["lists"]["pres-2022-1.X"] == {"label": "Candidat X", "family": "gauche"}
    el = json.loads((tmp_path / "elections" / "pres-2022-1.json").read_text())
    assert el["lists"] == ["pres-2022-1.X"]
    assert el["territories"]["FR"] == [10, 8, 1, 1, 8, 8]  # inscrits, votants, blancs, nuls, exprimés, voix par liste
    names = json.loads((tmp_path / "names.json").read_text())
    assert names["FR"] == "France"


def test_write_parents_links_communes_to_departments_and_departments_to_regions(tmp_path):
    import polars as pl

    from oripol_etl.export import write_parents

    geo = pl.DataFrame(
        {
            "code": ["69123", "69266", "97411", "98735", "ZZ042"],
            "dep": ["69", "69", "974", "987", "ZZ"],
            "reg": ["84", "84", "04", "987", None],
        }
    )
    write_parents(tmp_path, geo)
    parents = json.loads((tmp_path / "parents.json").read_text())
    assert parents["COM-69123"] == "DEP-69"
    assert parents["COM-69266"] == "DEP-69"
    assert parents["DEP-69"] == "REG-84"
    assert parents["DEP-974"] == "REG-04"
    assert parents["DEP-987"] == "REG-987"
    assert "DEP-ZZ" not in parents  # Français de l'étranger : pas de région
    assert not any(k.startswith("COM-ZZ") for k in parents)  # pas de commune dans le département fictif
