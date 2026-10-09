"""Télécharge les contours actuels et construit web/static/data/contours.pmtiles.

- régions / départements de métropole : france-geojson (d'après IGN Admin Express). Les versions « avec outre-mer »
  repositionnent les DOM près de la métropole : on reconstruit donc les DOM à partir de leurs communes (vraies coordonnées) ;
- communes (toutes) : API Découpage administratif, département par département ;
- collectivités d'outre-mer : communes via l'API, regroupées sous leur collectivité (DEP-975, REG-975…).
Identifiants : REG-<code>, DEP-<code>, COM-<code INSEE>.
"""
import copy
import csv
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from oripol_etl.bounds import bbox, merge_bboxes
from oripol_etl.dissolve import dissolve

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "web" / "static" / "data"
TMP = ROOT / "data" / "contours"
RAW = ROOT / "data" / "raw"
API = "https://geo.api.gouv.fr"
GEOJSON = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master"
PARAMS = {"fields": "nom,code", "format": "geojson", "geometry": "contour"}
DOM_REGIONS = {"971": "01", "972": "02", "973": "03", "974": "04", "976": "06"}  # département -> code région


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


def write_bounds() -> None:
    """Emprise de chaque territoire (id -> [ouest, sud, est, nord]) pour zoomer dessus depuis la recherche."""
    boxes: dict[str, list] = {}
    for name in ("regions", "departements", "communes"):
        fc = json.loads((TMP / f"{name}.geojson").read_text(encoding="utf-8"))
        for f in fc["features"]:
            boxes.setdefault(f["properties"]["id"], []).append(bbox(f["geometry"]))
    merged = {k: list(merge_bboxes(v)) for k, v in boxes.items()}
    merged["FR"] = [-5.5, 41.2, 9.8, 51.2]  # France métropolitaine
    (OUT / "bounds.json").write_text(json.dumps(merged, separators=(",", ":")), encoding="utf-8")


def build_tiles() -> None:
    # la couche communes (35 000 polygones) n'est embarquée qu'à partir du zoom 6 : chargement initial rapide.
    # Tippecanoe ignore le zoom minimal posé sur la couche : on le pose sur chaque entité.
    src = TMP / "communes.geojson"
    fc = json.loads(src.read_text(encoding="utf-8"))
    for f in fc["features"]:
        f["tippecanoe"] = {"minzoom": 6}
    tiled = TMP / "communes.tiled.geojson"
    tiled.write_text(json.dumps(fc), encoding="utf-8")
    args = ["tippecanoe", "-o", str(OUT / "contours.pmtiles"), "-Z0", "-z10", "--drop-densest-as-needed",
            "--simplify-only-low-zooms", "--force", "-q"]
    args += ["-L", f"regions:{TMP / 'regions.geojson'}", "-L", f"departements:{TMP / 'departements.geojson'}",
             "-L", f"communes:{tiled}"]
    subprocess.run(args, check=True)


def main() -> None:
    if "--tiles-only" in sys.argv:  # réutilise les GeoJSON déjà téléchargés
        write_bounds()
        build_tiles()
        return
    TMP.mkdir(parents=True, exist_ok=True)
    names: dict[str, str] = {"FR": "France"}
    with httpx.Client(follow_redirects=True) as client:
        regions = get_json(client, f"{GEOJSON}/regions-version-simplifiee.geojson")["features"]
        departements = get_json(client, f"{GEOJSON}/departements-version-simplifiee.geojson")["features"]
        api_deps = get_json(client, f"{API}/departements")
        dep_codes = [d["code"] for d in api_deps]
        dep_names = {d["code"]: d["nom"] for d in api_deps}

        def commune_dep(code: str) -> list[dict]:
            fc = get_json(client, f"{API}/communes", {**PARAMS, "codeDepartement": code})
            return fc["features"] if fc else []

        with ThreadPoolExecutor(max_workers=6) as pool:
            by_dep = dict(zip(dep_codes, pool.map(commune_dep, dep_codes)))
            communes = [f for fs in by_dep.values() for f in fs]
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
    for dep, region in DOM_REGIONS.items():  # DOM : département et région reconstruits depuis leurs communes
        label = dep_names[dep]
        layers["departements"].append(dissolve(by_dep[dep], f"DEP-{dep}", label))
        layers["regions"].append(dissolve(by_dep[dep], f"REG-{region}", label))
        names[f"DEP-{dep}"] = label
        names[f"REG-{region}"] = label
    by_collectivite: dict[str, list[dict]] = {}
    labels: dict[str, str] = {}
    for f, collectivite, label in comer_polys:
        labels[collectivite] = label
        layers["communes"] += tagged([f], "COM")
        by_collectivite.setdefault(collectivite, []).append(f)
        for prefix in ("DEP", "REG"):
            names[f"{prefix}-{collectivite}"] = label
    for collectivite, fs in by_collectivite.items():  # collectivités d'outre-mer : un polygone par département/région
        layers["departements"].append(dissolve(fs, f"DEP-{collectivite}", labels[collectivite]))
        layers["regions"].append(dissolve(fs, f"REG-{collectivite}", labels[collectivite]))
    for fs in layers.values():
        for f in fs:
            names.setdefault(f["properties"]["id"], f["properties"]["name"])  # les noms posés explicitement priment

    for name, fs in layers.items():
        (TMP / f"{name}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": fs}), encoding="utf-8")
    write_bounds()
    build_tiles()

    names_path = OUT / "names.json"
    existing = json.loads(names_path.read_text(encoding="utf-8")) if names_path.exists() else {}
    names_path.write_text(json.dumps({**existing, **names}, ensure_ascii=False), encoding="utf-8")
    print("OK", len(names), "noms,", len(layers["communes"]), "communes")


if __name__ == "__main__":
    main()
