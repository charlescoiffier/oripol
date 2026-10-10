import polars as pl

from oripol_etl.cog import CommuneResolver
from oripol_etl.ministry import ColumnMap, election_id_from_source, to_commune_tables

CM = ColumnMap(
    election_id="id_election",
    bureau_id="bv",
    commune_code=pl.col("code_commune"),
    inscrits="inscrits",
    votants="votants",
    blancs="blancs",
    nuls="nuls",
    exprimes="exprimes",
    cand_election_id="id_election",
    cand_bureau_id="bv",
    cand_name="nom",
    cand_nuance="nuance",
    cand_votes="voix",
)


def test_election_id_from_source():
    assert election_id_from_source("2022_pres_t1") == "pres-2022-1"
    assert election_id_from_source("2022_pres_t2") == "pres-2022-2"
    assert election_id_from_source("2022_legi_t1") == "legi-2022-1"
    assert election_id_from_source("2022_legi_t2") == "legi-2022-2"
    assert election_id_from_source("2022_euro_t1") is None  # pas encore pris en charge


def general():
    return pl.DataFrame(
        {
            "id_election": ["2022_pres_t1"] * 4 + ["2022_pres_t2"],
            "bv": ["b1", "b2", "b3", "b4", "b5"],
            "code_commune": ["11111", "22222", "75108", "ZZ", "11111"],
            "inscrits": [100, 50, 200, 10, 100],
            "votants": [80, 40, 150, 5, 80],
            "blancs": [2, 1, 5, 0, 2],
            "nuls": [1, 1, 3, 0, 1],
            "exprimes": [77, 38, 142, 5, 77],
        }
    )


def candidates():
    return pl.DataFrame(
        {
            "id_election": ["2022_pres_t1"] * 8 + ["2022_pres_t2"],
            "bv": ["b1", "b1", "b2", "b2", "b3", "b3", "b4", "b4", "b5"],
            "nom": ["Macron", "Le Pen", "Macron", "Le Pen", "Macron", "Mélenchon", "Macron", "Le Pen", "Macron"],
            "nuance": [None] * 9,
            "voix": [40, 37, 20, 18, 100, 42, 3, 2, 77],
        }
    )


def test_aggregates_bureaux_to_resolved_communes_and_keeps_supported_rounds():
    resolver = CommuneResolver({"11111": "22222"}, {"22222", "75056"})
    part, votes = to_commune_tables(general(), candidates(), CM, resolver)

    p = part.filter((pl.col("code") == "22222") & (pl.col("election_id") == "pres-2022-1")).to_dicts()[0]
    assert p["election_id"] == "pres-2022-1"
    assert (p["inscrits"], p["exprimes"]) == (150, 115)  # b1 + b2 fusionnées

    assert part.filter(pl.col("code") == "75056")["exprimes"].item() == 142  # arrondissement → Paris
    assert part.filter(pl.col("election_id") != "pres-2022-1").height == 1  # le 2d tour (b5) est désormais conservé

    v = votes.filter(
        (pl.col("code") == "22222") & (pl.col("list_key") == "MACRON") & (pl.col("election_id") == "pres-2022-1")
    )
    assert v["voix"].item() == 60
    assert votes.filter(pl.col("list_key") == "MELENCHON")["voix"].item() == 42


def test_codes_outside_cog_are_kept_untouched_for_later_filtering():
    resolver = CommuneResolver({}, {"22222"})
    part, _ = to_commune_tables(general(), candidates(), CM, resolver)
    assert "ZZ" in part["code"].to_list()


def test_legislative_votes_are_keyed_by_nuance_not_by_name():
    general = pl.DataFrame(
        {
            "id_election": ["2022_legi_t1"] * 2,
            "bv": ["b1", "b2"],
            "code_commune": ["22222", "22222"],
            "inscrits": [100, 100],
            "votants": [80, 80],
            "blancs": [1, 1],
            "nuls": [1, 1],
            "exprimes": [78, 78],
        }
    )
    candidates = pl.DataFrame(
        {
            "id_election": ["2022_legi_t1"] * 4,
            "bv": ["b1", "b1", "b2", "b2"],
            "nom": ["Dupont", "Martin", "Durand", "Petit"],
            "nuance": ["ENS", "RN", "ENS", "NUP"],
            "voix": [40, 38, 30, 48],
        }
    )
    resolver = CommuneResolver({}, {"22222"})
    part, votes = to_commune_tables(general, candidates, CM, resolver)
    assert part["election_id"].unique().to_list() == ["legi-2022-1"]
    v = {r["list_key"]: r["voix"] for r in votes.iter_rows(named=True)}
    assert v == {"ENS": 70, "RN": 38, "NUP": 48}  # candidats de même nuance regroupés
