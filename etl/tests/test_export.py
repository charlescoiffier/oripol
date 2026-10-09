import json

from oripol_etl.export import write_site_data
from oripol_etl.families import Family, ListMapping


def test_writes_prefixed_list_ids_and_index(tmp_path):
    families = [Family("gauche", "Gauche", -1, "#f00")]
    mappings = {"pres-2022-1": {"X": ListMapping("X", "Candidat X", "gauche")}}
    payloads = {
        "pres-2022-1": {
            "FR": {"inscrits": 10, "votants": 8, "blancs": 0, "nuls": 0, "exprimes": 8, "voix": {"X": 8}, "precision": "commune"}
        }
    }
    write_site_data(tmp_path, families, mappings, payloads, names={"FR": "France"})
    idx = json.loads((tmp_path / "index.json").read_text())
    assert idx["elections"] == [{"id": "pres-2022-1", "type": "pres", "year": 2022, "round": 1, "label": "Présidentielle 2022 – 1er tour"}]
    cls = json.loads((tmp_path / "classification.json").read_text())
    assert cls["lists"]["pres-2022-1.X"] == {"label": "Candidat X", "family": "gauche"}
    el = json.loads((tmp_path / "elections" / "pres-2022-1.json").read_text())
    assert el["territories"]["FR"]["voix"] == {"pres-2022-1.X": 8}
    names = json.loads((tmp_path / "names.json").read_text())
    assert names["FR"] == "France"
