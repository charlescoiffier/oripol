from __future__ import annotations

from shapely import make_valid
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

SIMPLIFY_TOLERANCE = 0.0004  # degrés (~40 m) : invisible à l'échelle d'un département ou d'une région


def _polygonal(geom):
    """Ne garde que les surfaces : la réparation d'une géométrie invalide peut laisser des lignes ou des points."""
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    parts = [g for g in getattr(geom, "geoms", []) if g.geom_type in ("Polygon", "MultiPolygon")]
    return unary_union(parts)


def _repaired_polygons(geom) -> list:
    """Chaque partie est réparée séparément : une partie dégénérée est écartée au lieu de faire échouer l'ensemble."""
    parts = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    out = []
    for part in parts:
        try:
            fixed = _polygonal(make_valid(part))
        except Exception:  # noqa: BLE001 - GEOS lève des exceptions variées sur les parties écrasées
            fixed = part.buffer(0)
        if not fixed.is_empty and fixed.area > 0:
            out.append(fixed)
    return out


def dissolve(features: list[dict], feature_id: str, name: str) -> dict:
    """Fusionne des polygones (ex. les communes d'un DOM) en une seule entité simplifiée."""
    merged = unary_union([p for f in features for p in _repaired_polygons(shape(f["geometry"]))])
    merged = _polygonal(merged).simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
    merged = _polygonal(merged)
    return {"type": "Feature", "properties": {"id": feature_id, "name": name}, "geometry": mapping(merged)}
