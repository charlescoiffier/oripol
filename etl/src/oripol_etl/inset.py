"""Placement des territoires d'outre-mer en encart, dans la carte générale (bas gauche de la métropole)."""
from __future__ import annotations

import math
from copy import deepcopy


def _map_coords(coords, fn):
    if coords and isinstance(coords[0], (int, float)):
        return list(fn(coords[0], coords[1]))
    return [_map_coords(c, fn) for c in coords]


def transform_geometry(geometry: dict, src_center: tuple[float, float], dst_center: tuple[float, float], scale: float) -> dict:
    """Translate et met à l'échelle une géométrie en conservant sa forme réelle.

    Les degrés de longitude rétrécissent avec la latitude : on travaille en « mètres locaux » (longitude x cos φ)
    puis on les reconvertit à la latitude de destination, pour que la forme affichée reste fidèle."""
    k_src = math.cos(math.radians(src_center[1]))
    k_dst = math.cos(math.radians(dst_center[1]))

    def fn(lon: float, lat: float):
        x = (lon - src_center[0]) * k_src
        y = lat - src_center[1]
        return (round(dst_center[0] + scale * x / k_dst, 5), round(dst_center[1] + scale * y, 5))

    out = deepcopy(geometry)
    out["coordinates"] = _map_coords(geometry["coordinates"], fn)
    return out


def fit_scale(bb: tuple[float, float, float, float], box_w: float, box_h: float, src_lat: float, dst_lat: float) -> float:
    """Facteur d'échelle maximal pour que l'emprise tienne dans la boîte (en degrés à la latitude de destination)."""
    k_src = math.cos(math.radians(src_lat))
    k_dst = math.cos(math.radians(dst_lat))
    w = (bb[2] - bb[0]) * k_src
    h = bb[3] - bb[1]
    return min(box_w * k_dst / w, box_h / h)


def boxes(count: int, cols: int, left: float, top: float, box_w: float, box_h: float, gap: float):
    """Cases (ouest, sud, est, nord) rangées de gauche à droite puis de haut en bas."""
    cells = []
    for i in range(count):
        row, col = divmod(i, cols)
        west = round(left + col * (box_w + gap), 4)
        north = round(top - row * (box_h + gap), 4)
        cells.append((west, round(north - box_h, 4), round(west + box_w, 4), north))
    return cells
