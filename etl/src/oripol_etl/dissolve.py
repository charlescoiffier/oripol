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


def dissolve(features: list[dict], feature_id: str, name: str) -> dict:
    """Fusionne des polygones (ex. les communes d'un DOM) en une seule entité simplifiée."""
    merged = unary_union([make_valid(shape(f["geometry"])) for f in features])
    merged = _polygonal(merged).simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
    merged = _polygonal(merged)
    return {"type": "Feature", "properties": {"id": feature_id, "name": name}, "geometry": mapping(merged)}
