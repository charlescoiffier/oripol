#!/usr/bin/env bash
# Régénère les données du site (résultats + contours) à partir des sources officielles.
# Télécharge ~240 Mo la première fois ; nécessite uv et tippecanoe (brew install uv tippecanoe).
set -euo pipefail
cd "$(dirname "$0")/etl"
uv sync
uv run python scripts/fetch_sources.py
uv run python -m oripol_etl.pipeline
uv run python scripts/fetch_contours.py
echo "Données prêtes dans web/static/data"
