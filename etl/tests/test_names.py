import polars as pl

from oripol_etl.aggregate import build_names
from oripol_etl.cog import CommuneResolver
from oripol_etl.ministry import ColumnMap, to_commune_names

CM = ColumnMap(
    election_id="id_election", bureau_id="bv", commune_code=pl.col("code_commune"),
    inscrits="inscrits", votants="votants", blancs="blancs", nuls="nuls", exprimes="exprimes",
    cand_election_id="id_election", cand_bureau_id="bv", cand_name="nom", cand_nuance="nuance",
    cand_list_label="libelle_abrege_liste", cand_votes="voix",
)
RESOLVER = CommuneResolver({}, {"A1", "A2", "B1"})


def general():
    return pl.DataFrame(
        {
            "id_election": ["2022_legi_t1"] * 3 + ["2022_pres_t1"],
            "bv": ["b1", "b2", "b3", "b4"],
            "code_commune": ["A1", "A2", "B1", "A1"],
            "inscrits": [1] * 4, "votants": [1] * 4, "blancs": [0] * 4, "nuls": [0] * 4, "exprimes": [1] * 4,
        }
    )


def candidates():
    return pl.DataFrame(
        {
            "id_election": ["2022_legi_t1"] * 6 + ["2022_pres_t1"],
            "bv": ["b1", "b1", "b2", "b2", "b3", "b3", "b4"],
            "nom": ["DUPONT", "MARTIN", "DUPONT", "MARTIN", "DURAND", "NC LISTE", "MACRON"],
            "prenom": ["Jean", "Anne", "Jean", "Anne", "Paul", "Zoé", "Emmanuel"],
            "nuance": ["DVG", "LR", "DVG", "LR", "DVG", None, None],
            "libelle_abrege_liste": [None] * 7,
            "voix": [1] * 7,
        }
    )


def test_names_are_firstname_then_name_per_commune_and_nuance():
    n = to_commune_names(general(), candidates(), CM, RESOLVER)
    got = {(r["election_id"], r["code"], r["list_key"]): r["person"] for r in n.to_dicts()}
    assert got[("legi-2022-1", "A1", "DVG")] == "Jean DUPONT"
    assert got[("legi-2022-1", "A2", "LR")] == "Anne MARTIN"
    assert got[("legi-2022-1", "B1", "DVG")] == "Paul DURAND"


def test_presidential_and_unlabelled_lists_have_no_names():
    n = to_commune_names(general(), candidates(), CM, RESOLVER)
    assert set(n["election_id"]) == {"legi-2022-1"}
    assert "NC" not in set(n["list_key"])


GEO = pl.DataFrame({"code": ["A1", "A2", "B1"], "dep": ["01", "01", "02"], "reg": ["R1", "R1", "R1"]})


def names(rows):
    return pl.DataFrame(
        [{"election_id": "e", "code": c, "list_key": k, "person": p} for c, k, p in rows],
        schema={"election_id": pl.String, "code": pl.String, "list_key": pl.String, "person": pl.String},
    )


def test_aggregated_territories_keep_a_name_only_when_unique():
    out = build_names("e", names([("A1", "LR", "Anne MARTIN"), ("A2", "LR", "Anne MARTIN"), ("B1", "LR", "Luc BLOC"),
                                  ("A1", "DVG", "Jean DUPONT")]), GEO)
    assert out["COM-A1"] == {"LR": "Anne MARTIN", "DVG": "Jean DUPONT"}
    assert out["DEP-01"] == {"LR": "Anne MARTIN", "DVG": "Jean DUPONT"}  # un seul nom dans le département
    assert "DEP-02" in out and out["DEP-02"] == {"LR": "Luc BLOC"}
    assert out["REG-R1"] == {"DVG": "Jean DUPONT"}  # deux têtes de liste LR différentes : aucun nom
    assert out["FR"] == {"DVG": "Jean DUPONT"}


def test_a_commune_with_several_people_for_one_nuance_lists_them():
    out = build_names("e", names([("A1", "DVG", "Jean DUPONT"), ("A1", "DVG", "Paul DURAND")]), GEO)
    assert out["COM-A1"] == {"DVG": "Jean DUPONT / Paul DURAND"}
    assert "DEP-01" not in out  # plusieurs personnes : pas de nom pour le département
