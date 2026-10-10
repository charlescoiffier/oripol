from pathlib import Path

import polars as pl

from .ministry import ColumnMap

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT.parent / "web" / "static" / "data"
FAMILIES = ROOT / "mappings" / "families.yaml"
MAPPINGS = [ROOT / "mappings" / "presidentielle.yaml", ROOT / "mappings" / "legislatives.yaml"]

# --- COG Insee millésime 2026 (colonnes lues en minuscules) ---
COG_COMMUNES = RAW / "v_commune.csv"  # typecom, com, dep, reg
COG_MOUVEMENTS = RAW / "v_mvt_commune.csv"  # mod, date_eff, typecom_av, com_av, typecom_ap, com_ap
COG_COMER_COMMUNES = RAW / "v_commune_comer.csv"  # com_comer, libelle, comer, libelle_comer
COG_COMER = RAW / "v_comer.csv"  # comer, libelle

# --- Élections agrégées (data.gouv.fr) ---
GENERAL_FILE = RAW / "general_results.parquet"
CANDIDATES_FILE = RAW / "candidats_results.parquet"
COLUMNS = ColumnMap(
    election_id="id_election",
    bureau_id="id_brut_miom",
    commune_code=pl.col("code_commune"),
    inscrits="inscrits",
    votants="votants",
    blancs="blancs",
    nuls="nuls",
    exprimes="exprimes",
    cand_election_id="id_election",
    cand_bureau_id="id_brut_miom",
    cand_name="nom",
    cand_nuance="nuance",
    cand_votes="voix",
)
