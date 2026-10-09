#!/usr/bin/env bash
# Lance le serveur de développement et ouvre le site dans le navigateur.
# Génère d'abord les données si elles sont absentes (voir build-data.sh).
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
if [ ! -f "$root/web/static/data/contours.pmtiles" ]; then
	echo "Données absentes : génération (téléchargement ~240 Mo)…"
	"$root/build-data.sh"
fi
cd "$root/web"
[ -d node_modules ] || npm install --engine-strict=false
exec npm run dev -- --port 5173 --open
