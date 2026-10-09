from __future__ import annotations

BBox = tuple[float, float, float, float]


def _points(coords):
    if coords and isinstance(coords[0], (int, float)):
        yield coords
    else:
        for c in coords:
            yield from _points(c)


def bbox(geometry: dict) -> BBox:
    """Emprise (ouest, sud, est, nord) d'une géométrie GeoJSON, arrondie à 4 décimales."""
    xs, ys = [], []
    for x, y, *_ in _points(geometry["coordinates"]):
        xs.append(x)
        ys.append(y)
    return (round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4))


def merge_bboxes(boxes: list[BBox]) -> BBox:
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )
