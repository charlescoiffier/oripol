"""Télécharge les contours actuels (API Découpage administratif) et construit contours.pmtiles."""
import json
import subprocess
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parents[2] / "web" / "static" / "data"
TMP = Path(__file__).resolve().parents[1] / "data" / "contours"
API = "https://geo.api.gouv.fr"
PARAMS = {"fields": "nom,code", "format": "geojson", "geometry": "contour"}


GEOJSON = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master"


def collection(name: str, prefix: str) -> dict:
    # L'API geo ne fournit pas les contours régions/départements : france-geojson (d'après IGN Admin Express)
    r = httpx.get(f"{GEOJSON}/{name}-avec-outre-mer.geojson", follow_redirects=True, timeout=120)
    r.raise_for_status()
    return tag(r.json(), prefix)


def tag(fc: dict, prefix: str) -> dict:
    for f in fc["features"]:
        f["properties"] = {"id": f"{prefix}-{f['properties']['code']}", "name": f["properties"]["nom"]}
    return fc


def main() -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    layers = {
        "regions": collection("regions", "REG"),
        "departements": collection("departements", "DEP"),
    }
    targets = (OUT / "targets.txt").read_text(encoding="utf-8").split()
    features = []
    for code in targets:
        r = httpx.get(f"{API}/communes/{code}", params=PARAMS, timeout=60)
        if r.status_code != 200:
            print("contour introuvable:", code)
            continue
        features.append(r.json())
    layers["communes"] = tag({"type": "FeatureCollection", "features": features}, "COM")

    names: dict[str, str] = {"FR": "France"}
    args = ["tippecanoe", "-o", str(OUT / "contours.pmtiles"), "-zg", "--drop-densest-as-needed", "--force", "-q"]
    for name, fc in layers.items():
        p = TMP / f"{name}.geojson"
        p.write_text(json.dumps(fc), encoding="utf-8")
        args += ["-L", f"{name}:{p}"]
        names.update({f["properties"]["id"]: f["properties"]["name"] for f in fc["features"]})
    subprocess.run(args, check=True)

    names_path = OUT / "names.json"
    existing = json.loads(names_path.read_text(encoding="utf-8")) if names_path.exists() else {}
    names_path.write_text(json.dumps({**existing, **names}, ensure_ascii=False), encoding="utf-8")
    print("OK", len(names), "noms")


if __name__ == "__main__":
    main()
