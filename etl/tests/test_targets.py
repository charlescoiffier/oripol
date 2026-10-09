import polars as pl

from oripol_etl.cog import CommuneResolver
from oripol_etl.targets import chefs_lieux, population_max, select_targets


def test_population_max_takes_max_over_numeric_columns_excluding_ids():
    df = pl.DataFrame(
        {"CODGEO": ["A", "B"], "REG": [11, 11], "P1900": [10.0, 40000.0], "P2020": [35000.0, 100.0]}
    )
    out = population_max(df, "CODGEO", ["REG"]).sort("code")
    assert out["code"].to_list() == ["A", "B"]
    assert out["max_population"].to_list() == [35000.0, 40000.0]


def test_chefs_lieux_distinguishes_prefecture_from_sous_prefecture():
    deps = pl.DataFrame({"dep": ["01"], "cheflieu": ["01053"]})
    arrs = pl.DataFrame({"arr": ["011", "012"], "cheflieu": ["01053", "01004"]})
    out = chefs_lieux(deps, arrs).sort("code")
    assert out.to_dicts() == [
        {"code": "01004", "motif": "sous_prefecture"},
        {"code": "01053", "motif": "prefecture"},
    ]


def test_select_targets_unions_and_resolves_codes():
    max_pop = pl.DataFrame(
        {"code": ["01053", "99999", "11111"], "max_population": [40000.0, 5000.0, 31000.0]}
    )
    lieux = pl.DataFrame({"code": ["01053", "01004"], "motif": ["prefecture", "sous_prefecture"]})
    # 11111 a fusionné dans 22222 : la population doit être rattachée à 22222
    resolver = CommuneResolver({"11111": "22222"}, {"01053", "01004", "99999", "22222"})
    out = select_targets(max_pop, lieux, resolver)
    assert out.sort("code").to_dicts() == [
        {"code": "01004", "motifs": "sous_prefecture"},
        {"code": "01053", "motifs": "prefecture,seuil_30000"},
        {"code": "22222", "motifs": "seuil_30000"},
    ]
