"""Télécharge les sources officielles dans etl/data/raw (ignore celles déjà présentes)."""
from pathlib import Path

import httpx

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
COG = "https://www.insee.fr/fr/statistiques/fichier/8740222"  # Code officiel géographique, millésime 2026
ELECTIONS = "https://data-pipeline-open.s3.sbg.io.cloud.ovh.net/elections"  # data.gouv.fr « Données des élections agrégées »

SOURCES = {
    "general_results.parquet": f"{ELECTIONS}/general_results.parquet",  # ~70 Mo
    "candidats_results.parquet": f"{ELECTIONS}/candidats_results.parquet",  # ~160 Mo
    "v_commune.csv": f"{COG}/v_commune_2026.csv",
    "v_mvt_commune.csv": f"{COG}/v_mvt_commune_2026.csv",
    "v_commune_comer.csv": f"{COG}/v_commune_comer_2026.csv",
    "v_comer.csv": f"{COG}/v_comer_2026.csv",
}


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        dest = RAW / name
        if dest.exists():
            print("déjà présent :", name)
            continue
        print("téléchargement :", name)
        with httpx.stream("GET", url, follow_redirects=True, timeout=None) as r, dest.open("wb") as f:
            r.raise_for_status()
            for chunk in r.iter_bytes():
                f.write(chunk)


if __name__ == "__main__":
    main()
