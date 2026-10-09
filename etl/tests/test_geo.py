import polars as pl

from oripol_etl.geo import build_geo


def test_build_geo_merges_cog_comer_and_abroad():
    communes = pl.DataFrame({"com": ["69123", "2A004"], "dep": ["69", "2A"], "reg": ["84", "94"]})
    comer = pl.DataFrame({"com_comer": ["98735", "97801", "98611"], "comer": ["987", "978", "986"]})
    geo = build_geo(communes, comer, election_codes=["69123", "98735", "98601", "ZZ042", "ZZ077", "26383"])
    rows = {r["code"]: (r["dep"], r["reg"]) for r in geo.iter_rows(named=True)}
    assert rows["69123"] == ("69", "84")
    assert rows["2A004"] == ("2A", "94")  # communes du COG présentes même sans résultat
    assert rows["98735"] == ("987", "987")  # collectivité d'outre-mer = son propre département et région
    assert rows["97801"] == ("978", "978")
    assert rows["98601"] == ("986", "986")  # collectivité entière (Wallis-et-Futuna) sans commune propre
    assert rows["ZZ042"] == ("ZZ", None)  # Français établis hors de France
    assert rows["ZZ077"] == ("ZZ", None)
    assert "26383" not in rows  # code inconnu : reste non résolu (contrôlé par validate_coverage)
