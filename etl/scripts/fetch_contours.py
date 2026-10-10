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
from oripol_etl.inset import boxes, fit_scale, transform_geometry

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "web" / "static" / "data"
TMP = ROOT / "data" / "contours"
RAW = ROOT / "data" / "raw"
API = "https://geo.api.gouv.fr"
GEOJSON = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master"
PARAMS = {"fields": "nom,code", "format": "geojson", "geometry": "contour"}
DOM_REGIONS = {"971": "01", "972": "02", "973": "03", "974": "04", "976": "06"}  # département -> code région
SKIPPED_DEPS = {"984", "989"}  # TAAF, Clipperton : pas de résultats électoraux
# Territoires d'outre-mer, dans l'ordre de l'encart (clé, code collectivité pour les COM)
OVERSEAS = ["971", "972", "973", "974", "976", "975", "977", "978", "987", "988", "986"]
INSET = {"cols": 4, "left": -5.4, "top": 41.0, "box_w": 1.55, "box_h": 1.1, "gap": 0.12}  # degrés, sous le sud-ouest de la métropole


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
    merged["FR"] = [-5.8, 37.2, 9.9, 51.3]  # métropole + encart outre-mer
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
             "-L", f"communes:{tiled}", "-L", f"inset:{TMP / 'inset.geojson'}"]
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
        api_deps = [d for d in get_json(client, f"{API}/departements") if d["code"] not in SKIPPED_DEPS]
        dep_codes = [d["code"] for d in api_deps]
        dep_names = {d["code"]: d["nom"] for d in api_deps}

        def commune_dep(code: str) -> list[dict]:
            fc = get_json(client, f"{API}/communes", {**PARAMS, "codeDepartement": code})
            return fc["features"] if fc else []

        with ThreadPoolExecutor(max_workers=6) as pool:
            by_dep = dict(zip(dep_codes, pool.map(commune_dep, dep_codes)))
            comer = read_comer()
            comer_features = pool.map(lambda t: get_json(client, f"{API}/communes/{t[0]}", PARAMS), comer)
        comer_polys = [(f, c, lab) for f, (_, c, lab) in zip(comer_features, comer) if f]

    # territoires d'outre-mer : communes brutes (vraies coordonnées), libellé, code région
    groups: dict[str, dict] = {}
    for dep, region in DOM_REGIONS.items():
        groups[dep] = {"label": dep_names[dep], "region": region, "communes": by_dep[dep]}
    for f, collectivite, label in comer_polys:
        g = groups.setdefault(collectivite, {"label": label, "region": collectivite, "communes": []})
        g["communes"].append(f)
    # Saint-Barthélemy et Saint-Martin partagent le libellé COG « collectivité » : on garde leurs noms propres
    for code in ("977", "978"):
        if code in groups and groups[code]["communes"]:
            groups[code]["label"] = groups[code]["communes"][0]["properties"]["nom"]

    layers = {
        "regions": tagged(regions, "REG"),
        "departements": tagged(departements, "DEP"),
        "communes": tagged([f for dep, fs in by_dep.items() if dep not in DOM_REGIONS for f in fs], "COM"),
        "inset": [],
    }
    cells = boxes(len(OVERSEAS), **{k: INSET[k] for k in ("cols", "left", "top", "box_w", "box_h", "gap")})
    for key, (west, south, east, north) in zip(OVERSEAS, cells):
        g = groups[key]
        src = merge_bboxes([bbox(f["geometry"]) for f in g["communes"]])
        src_center = ((src[0] + src[2]) / 2, (src[1] + src[3]) / 2)
        dst_center = ((west + east) / 2, (south + north) / 2)
        scale = 0.9 * fit_scale(src, east - west, north - south, src_center[1], dst_center[1])
        moved = []
        for f in g["communes"]:
            m = copy.deepcopy(f)
            m["geometry"] = transform_geometry(f["geometry"], src_center, dst_center, scale)
            moved.append(m)
        layers["communes"] += tagged(moved, "COM")
        layers["departements"].append(dissolve(moved, f"DEP-{key}", g["label"]))
        layers["regions"].append(dissolve(moved, f"REG-{g['region']}", g["label"]))
        names[f"DEP-{key}"] = names[f"REG-{g['region']}"] = g["label"]
        layers["inset"].append(
            {
                "type": "Feature",
                "properties": {"id": f"FRAME-{key}", "name": g["label"]},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
                },
            }
        )
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
