"""Vérifie que chaque fichier/colonne référencé par config.py existe vraiment."""
import polars as pl

from oripol_etl import config as c


def read(path):
    return pl.read_parquet(path) if str(path).endswith(".parquet") else pl.read_csv(path, infer_schema=False)


def need(df, cols, label):
    cols_l = {x.lower() for x in df.columns}
    missing = [x for x in cols if x.lower() not in cols_l]
    assert not missing, f"{label}: colonnes manquantes {missing}; présentes: {df.columns}"
    print("OK", label)


need(read(c.COG_COMMUNES), ["typecom", "com", "dep", "reg"], "COG communes")
need(read(c.COG_COMER_COMMUNES), ["com_comer", "comer"], "COG communes d'outre-mer")
need(read(c.COG_COMER), ["comer", "libelle"], "COG collectivités d'outre-mer")
need(read(c.COG_MOUVEMENTS), ["mod", "date_eff", "typecom_av", "com_av", "typecom_ap", "com_ap"], "COG mouvements")
g, k = read(c.GENERAL_FILE), read(c.CANDIDATES_FILE)
cm = c.COLUMNS
need(g, [cm.election_id, cm.bureau_id, cm.inscrits, cm.votants, cm.blancs, cm.nuls, cm.exprimes], "Général")
need(k, [cm.cand_election_id, cm.cand_bureau_id, cm.cand_name, cm.cand_votes], "Candidats")
code = g.select(cm.commune_code.alias("c")).head(5)["c"].to_list()
print("Exemples de code commune:", code)
ids = g[cm.election_id].unique().sort().to_list()
print("id_election exemples:", [i for i in ids if "pres" in str(i)][:12])
