#!/usr/bin/env bash
# Lance le serveur de développement et ouvre le site dans le navigateur.
set -euo pipefail
cd "$(dirname "$0")/web"
[ -d node_modules ] || npm install --engine-strict=false
exec npm run dev -- --port 5173 --open
