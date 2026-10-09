from pathlib import Path

import polars as pl

from .ministry import ColumnMap

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT.parent / "web" / "static" / "data"
MAPPING = ROOT / "mappings" / "presidentielle.yaml"

# --- COG Insee millésime 2026 (colonnes lues en minuscules) ---
COG_COMMUNES = RAW / "v_commune.csv"  # typecom, com, dep, reg
COG_DEPARTEMENTS = RAW / "v_departement.csv"  # dep, cheflieu
COG_ARRONDISSEMENTS = RAW / "v_arrondissement.csv"  # arr, cheflieu
COG_MOUVEMENTS = RAW / "v_mvt_commune.csv"  # mod, date_eff, typecom_av, com_av, typecom_ap, com_ap

# --- Populations historiques Insee (géographie 2025) ---
POP_FILE = RAW / "base-pop-historiques-1876-2023.xlsx"
POP_SHEET = "pop_1876_2023"
POP_HEADER_ROW = 5
POP_ID_COL = "CODGEO"
POP_EXCLUDE = ["REG", "DEP"]

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
    cand_votes="voix",
)
