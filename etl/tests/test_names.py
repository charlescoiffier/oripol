import polars as pl

from oripol_etl.aggregate import build_lists, build_names
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
            "libelle_abrege_liste": [None, None, None, None, None, "LISTE ZOÉ", None],
            "voix": [1, 2, 3, 4, 5, 6, 7],
        }
    )


def test_names_are_firstname_then_name_per_commune_and_nuance():
    n = to_commune_names(general(), candidates(), CM, RESOLVER)
    got = {(r["election_id"], r["code"], r["list_key"]): r["person"] for r in n.to_dicts()}
    assert got[("legi-2022-1", "A1", "DVG")] == "Jean DUPONT"
    assert got[("legi-2022-1", "A2", "LR")] == "Anne MARTIN"
    assert got[("legi-2022-1", "B1", "DVG")] == "Paul DURAND"


def test_votes_are_summed_per_commune_candidate_over_bureaux():
    n = to_commune_names(general(), candidates(), CM, RESOLVER)
    a1 = {r["person"]: r["voix"] for r in n.filter((pl.col("code") == "A1")).to_dicts()}
    assert a1 == {"Jean DUPONT": 1, "Anne MARTIN": 2}
    assert n.filter(pl.col("code") == "A2").filter(pl.col("person") == "Jean DUPONT")["voix"].item() == 3


def test_without_a_candidate_name_the_list_label_names_the_list():
    cand = pl.DataFrame(
        {"id_election": ["2026_muni_t1"] * 2, "bv": ["b1", "b1"], "nom": [None, None], "prenom": [None, None],
         "nuance": ["LDVG", None], "libelle_abrege_liste": ["AMBERIEU C'EST VOUS", "SANS NUANCE"], "voix": [10, 5]}
    )
    gen = pl.DataFrame(
        {"id_election": ["2026_muni_t1"], "bv": ["b1"], "code_commune": ["A1"], "inscrits": [1], "votants": [1],
         "blancs": [0], "nuls": [0], "exprimes": [1]}
    )
    n = to_commune_names(gen, cand, CM, RESOLVER)
    assert n.select("list_key", "person", "voix").to_dicts() == [
        {"list_key": "LDVG", "person": "AMBERIEU C'EST VOUS", "voix": 10}
    ]


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


def test_commune_lists_are_kept_one_by_one_with_their_votes():
    rows = names([("A1", "DVG", "Jean DUPONT"), ("A1", "DVG", "Paul DURAND"), ("A1", "LR", "Anne MARTIN")])
    rows = rows.with_columns(pl.Series("voix", [30, 10, 50]))
    assert build_lists("e", rows, GEO) == {"COM-A1": [("LR", "Anne MARTIN", 50), ("DVG", "Jean DUPONT", 30), ("DVG", "Paul DURAND", 10)]}


def test_aggregated_territories_keep_a_name_only_when_unique_and_not_repeated():
    out = build_names("e", names([("A1", "LR", "Anne MARTIN"), ("A2", "LR", "Anne MARTIN"), ("B1", "LR", "Luc BLOC"),
                                  ("A1", "DVG", "Jean DUPONT"), ("B1", "PS", "Eva RIVE")]), GEO)
    assert not any(t.startswith("COM-") for t in out)  # les communes ont leurs listes détaillées à part
    assert out["FR"] == {"DVG": "Jean DUPONT", "PS": "Eva RIVE"}  # LR : deux têtes de liste différentes, aucun nom
    assert out["DEP-01"] == {"LR": "Anne MARTIN"}  # seule LR de ce département : nom propre à ce territoire
    assert out["DEP-02"] == {"LR": "Luc BLOC"}
    assert "REG-R1" not in out  # ses noms uniques sont ceux du pays : le site s'y reporte


def test_several_people_for_one_nuance_give_no_name_to_aggregated_territories():
    out = build_names("e", names([("A1", "DVG", "Jean DUPONT"), ("A1", "DVG", "Paul DURAND")]), GEO)
    assert out == {}
