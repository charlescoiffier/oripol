from __future__ import annotations

from shapely import make_valid
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

SIMPLIFY_TOLERANCE = 0.0004  # degrés (~40 m) : invisible à l'échelle d'un département ou d'une région


def dissolve(features: list[dict], feature_id: str, name: str) -> dict:
    """Fusionne des polygones (ex. les communes d'un DOM) en une seule entité simplifiée."""
    merged = unary_union([make_valid(shape(f["geometry"])) for f in features])
    merged = merged.simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
    return {"type": "Feature", "properties": {"id": feature_id, "name": name}, "geometry": mapping(merged)}
