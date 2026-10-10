from oripol_etl.dissolve import dissolve


def square(x0, y0, x1, y1):
    return {
        "type": "Feature",
        "properties": {"id": "COM-x", "name": "commune"},
        "geometry": {"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]},
    }


def test_adjacent_communes_become_a_single_polygon_with_the_new_id_and_name():
    out = dissolve([square(0, 0, 1, 1), square(1, 0, 2, 1)], "DEP-974", "La Réunion")
    assert out["properties"] == {"id": "DEP-974", "name": "La Réunion"}
    assert out["geometry"]["type"] == "Polygon"
    xs = [p[0] for p in out["geometry"]["coordinates"][0]]
    assert (min(xs), max(xs)) == (0, 2)


def test_distant_parts_stay_in_one_multipolygon():
    out = dissolve([square(0, 0, 1, 1), square(10, 10, 11, 11)], "DEP-971", "Guadeloupe")
    assert out["geometry"]["type"] == "MultiPolygon"
    assert len(out["geometry"]["coordinates"]) == 2


def test_detail_is_simplified():
    # un côté avec un point presque aligné : la simplification le supprime
    feat = {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [0.5, 0.00001], [1, 0], [1, 1], [0, 1], [0, 0]]]},
    }
    out = dissolve([feat], "DEP-976", "Mayotte")
    assert len(out["geometry"]["coordinates"][0]) == 5  # 4 sommets + fermeture


def test_invalid_geometry_is_repaired_instead_of_crashing():
    bowtie = {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [2, 2], [2, 0], [0, 2], [0, 0]]]},
    }
    out = dissolve([bowtie, square(5, 5, 6, 6)], "DEP-988", "Nouvelle-Calédonie")
    assert out["geometry"]["type"] in {"Polygon", "MultiPolygon"}


def test_non_polygon_parts_are_dropped_so_the_result_is_always_polygonal():
    mixed = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "GeometryCollection",
            "geometries": [
                {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                {"type": "LineString", "coordinates": [[5, 5], [6, 6]]},
            ],
        },
    }
    out = dissolve([mixed], "DEP-989", "Clipperton")
    assert out["geometry"]["type"] in {"Polygon", "MultiPolygon"}


def test_mixed_dimension_input_is_unioned_without_crashing():
    mixed = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "GeometryCollection",
            "geometries": [
                {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                {"type": "LineString", "coordinates": [[5, 5], [6, 6]]},
            ],
        },
    }
    out = dissolve([mixed, square(1, 0, 2, 1)], "DEP-989", "Clipperton")  # square(x0, y0, x1, y1) : voisin du premier carré
    assert out["geometry"]["type"] in {"Polygon", "MultiPolygon"}


def test_degenerate_part_of_a_multipolygon_is_dropped_not_fatal():
    multi = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                [[[5, 5], [5.00001, 5], [5.00002, 5], [5, 5]]],  # anneau écrasé : aire nulle
            ],
        },
    }
    out = dissolve([multi], "DEP-986", "Wallis-et-Futuna")
    assert out["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    xs = [p[0] for poly in (out["geometry"]["coordinates"] if out["geometry"]["type"] == "MultiPolygon" else [out["geometry"]["coordinates"]]) for ring in poly for p in ring]
    assert max(xs) <= 1.0001  # la partie dégénérée a disparu
