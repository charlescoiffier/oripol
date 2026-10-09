"""Télécharge les contours actuels et construit web/static/data/contours.pmtiles.

- régions / départements : france-geojson (d'après IGN Admin Express), outre-mer inclus ;
- communes (toutes) : API Découpage administratif, département par département ;
- collectivités d'outre-mer : communes via l'API, regroupées sous leur collectivité (DEP-975, REG-975…).
Identifiants : REG-<code>, DEP-<code>, COM-<code INSEE>.
"""
import copy
import csv
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "web" / "static" / "data"
TMP = ROOT / "data" / "contours"
RAW = ROOT / "data" / "raw"
API = "https://geo.api.gouv.fr"
GEOJSON = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master"
PARAMS = {"fields": "nom,code", "format": "geojson", "geometry": "contour"}


def get_json(client: httpx.Client, url: str, params: dict | None = None):
    for attempt in range(4):
        try:
            r = client.get(url, params=params, timeout=180)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError:
            if attempt == 3:
                raise
    return None


def tagged(features: list[dict], prefix: str, code_of=lambda f: f["properties"]["code"]) -> list[dict]:
    out = []
    for f in features:
        g = copy.deepcopy(f)
        g["properties"] = {"id": f"{prefix}-{code_of(f)}", "name": f["properties"]["nom"]}
        out.append(g)
    return out


def read_comer() -> list[tuple[str, str, str]]:
    """(code commune, code collectivité, libellé collectivité) depuis le COG."""
    with (RAW / "v_commune_comer.csv").open(encoding="utf-8") as f:
        return [(r["COM_COMER"], r["COMER"], r["LIBELLE_COMER"]) for r in csv.DictReader(f)]


def main() -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    names: dict[str, str] = {"FR": "France"}
    with httpx.Client(follow_redirects=True) as client:
        regions = get_json(client, f"{GEOJSON}/regions-avec-outre-mer.geojson")["features"]
        departements = get_json(client, f"{GEOJSON}/departements-avec-outre-mer.geojson")["features"]
        dep_codes = [d["code"] for d in get_json(client, f"{API}/departements")]

        def commune_dep(code: str) -> list[dict]:
            fc = get_json(client, f"{API}/communes", {**PARAMS, "codeDepartement": code})
            return fc["features"] if fc else []

        with ThreadPoolExecutor(max_workers=6) as pool:
            communes = [f for fs in pool.map(commune_dep, dep_codes) for f in fs]
            comer = read_comer()
            comer_features = pool.map(
                lambda t: get_json(client, f"{API}/communes/{t[0]}", PARAMS), comer
            )
        comer_polys = [(f, c, lab) for f, (_, c, lab) in zip(comer_features, comer) if f]

    layers = {
        "regions": tagged(regions, "REG"),
        "departements": tagged(departements, "DEP"),
        "communes": tagged(communes, "COM"),
    }
    for f, collectivite, label in comer_polys:
        layers["communes"] += tagged([f], "COM")
        layers["departements"] += tagged([f], "DEP", lambda _f, c=collectivite: c)
        layers["regions"] += tagged([f], "REG", lambda _f, c=collectivite: c)
        for prefix in ("DEP", "REG"):
            names[f"{prefix}-{collectivite}"] = label
    for fs in layers.values():
        for f in fs:
            if not f["properties"]["id"].startswith(("DEP-9", "REG-9")) or f["properties"]["id"] not in names:
                names[f["properties"]["id"]] = f["properties"]["name"]

    args = ["tippecanoe", "-o", str(OUT / "contours.pmtiles"), "-Z0", "-z10", "--drop-densest-as-needed",
            "--simplify-only-low-zooms", "--force", "-q"]
    for name, fs in layers.items():
        p = TMP / f"{name}.geojson"
        p.write_text(json.dumps({"type": "FeatureCollection", "features": fs}), encoding="utf-8")
        args += ["-L", f"{name}:{p}"]
    subprocess.run(args, check=True)

    names_path = OUT / "names.json"
    existing = json.loads(names_path.read_text(encoding="utf-8")) if names_path.exists() else {}
    names_path.write_text(json.dumps({**existing, **names}, ensure_ascii=False), encoding="utf-8")
    print("OK", len(names), "noms,", len(layers["communes"]), "communes")


if __name__ == "__main__":
    main()
