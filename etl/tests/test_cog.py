import polars as pl

from oripol_etl.cog import build_resolver


def mouvements(rows):
    return pl.DataFrame(
        rows,
        schema={
            "MOD": pl.Int64,
            "DATE_EFF": pl.String,
            "TYPECOM_AV": pl.String,
            "COM_AV": pl.String,
            "TYPECOM_AP": pl.String,
            "COM_AP": pl.String,
        },
        orient="row",
    )


def test_simple_merge_maps_old_code_to_new():
    m = mouvements([(31, "2016-01-01", "COM", "11111", "COM", "22222")])
    r = build_resolver(m, {"22222"})
    assert r.resolve("11111") == "22222"
    assert r.resolve("22222") == "22222"


def test_chain_of_merges_resolves_to_final_commune():
    m = mouvements(
        [
            (31, "2010-01-01", "COM", "11111", "COM", "22222"),
            (32, "2019-01-01", "COM", "22222", "COM", "33333"),
        ]
    )
    r = build_resolver(m, {"33333"})
    assert r.resolve("11111") == "33333"


def test_restored_commune_is_not_remapped():
    m = mouvements(
        [
            (31, "2000-01-01", "COM", "11111", "COM", "22222"),
            (21, "2010-01-01", "COM", "22222", "COM", "11111"),
        ]
    )
    r = build_resolver(m, {"11111", "22222"})
    assert r.resolve("11111") == "11111"
    assert r.is_current("11111")


def test_municipal_arrondissements_resolve_to_city():
    r = build_resolver(mouvements([]), {"75056", "69123", "13055"})
    assert r.resolve("75108") == "75056"
    assert r.resolve("69383") == "69123"
    assert r.resolve("13208") == "13055"


def test_unknown_code_is_returned_unchanged_and_not_current():
    r = build_resolver(mouvements([]), {"22222"})
    assert r.resolve("99999") == "99999"
    assert not r.is_current("99999")


def test_cycle_does_not_loop_forever():
    m = mouvements(
        [
            (31, "2000-01-01", "COM", "11111", "COM", "22222"),
            (31, "2001-01-01", "COM", "22222", "COM", "11111"),
        ]
    )
    r = build_resolver(m, set())
    assert r.resolve("11111") in {"11111", "22222"}


def test_mod_given_as_text_is_supported():
    m = mouvements([(31, "2016-01-01", "COM", "2A001", "COM", "2A002")]).with_columns(
        pl.col("MOD").cast(pl.String)
    )
    r = build_resolver(m, {"2A002"})
    assert r.resolve("2A001") == "2A002"
