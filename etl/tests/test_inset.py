import math

from oripol_etl.bounds import bbox
from oripol_etl.inset import boxes, fit_scale, transform_geometry


def square(lon, lat, size):
    return {
        "type": "Polygon",
        "coordinates": [[[lon, lat], [lon + size, lat], [lon + size, lat + size], [lon, lat + size], [lon, lat]]],
    }


def test_transform_moves_the_source_centre_to_the_destination_centre():
    g = square(55, -22, 2)  # centre (56, -21)
    out = transform_geometry(g, src_center=(56, -21), dst_center=(-9, 38), scale=1.0)
    w, s, e, n = bbox(out)
    assert round((w + e) / 2, 2) == -9
    assert round((s + n) / 2, 2) == 38


def test_transform_keeps_the_true_shape_despite_latitude_change():
    g = square(0, -1, 2)  # carré de 2° x 2° centré sur l'équateur : forme réelle carrée
    out = transform_geometry(g, src_center=(1, 0), dst_center=(-9, 40), scale=1.0)
    w, s, e, n = bbox(out)
    # largeur réelle = degrés de longitude x cos(latitude) ; elle doit égaler la hauteur réelle (en degrés)
    assert math.isclose((e - w) * math.cos(math.radians(40)), n - s, rel_tol=0.01)


def test_fit_scale_makes_the_territory_fit_the_box():
    bb = (55.2, -21.4, 55.8, -20.8)
    scale = fit_scale(bb, box_w=2.0, box_h=1.5, src_lat=-21.1, dst_lat=38)
    g = square(55.2, -21.4, 0.6)
    out = transform_geometry(g, (55.5, -21.15), (0, 38), scale)
    w, s, e, n = bbox(out)
    assert e - w <= 2.0 + 1e-6 and n - s <= 1.5 + 1e-6


def test_boxes_are_laid_out_in_rows_without_overlap():
    cells = boxes(count=7, cols=3, left=-12, top=41.6, box_w=2.2, box_h=1.7, gap=0.2)
    assert len(cells) == 7
    assert cells[0] == (-12.0, 41.6 - 1.7, -12.0 + 2.2, 41.6)  # (ouest, sud, est, nord)
    assert cells[3][3] < cells[0][1]  # 2e rangée sous la 1re
    for i, a in enumerate(cells):
        for b in cells[i + 1:]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]
