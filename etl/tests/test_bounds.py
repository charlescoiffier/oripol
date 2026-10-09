from oripol_etl.bounds import bbox, merge_bboxes


def test_bbox_of_a_polygon():
    geom = {"type": "Polygon", "coordinates": [[[2, 45], [4, 45], [4, 47], [2, 47], [2, 45]]]}
    assert bbox(geom) == (2, 45, 4, 47)


def test_bbox_of_a_multipolygon_spans_all_parts():
    geom = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[0, 0], [1, 0], [1, 1], [0, 0]]],
            [[[10, 20], [12, 20], [12, 22], [10, 20]]],
        ],
    }
    assert bbox(geom) == (0, 0, 12, 22)


def test_merge_bboxes_takes_the_union():
    assert merge_bboxes([(0, 0, 1, 1), (5, -2, 6, 3)]) == (0, -2, 6, 3)


def test_bbox_rounds_to_four_decimals():
    geom = {"type": "Polygon", "coordinates": [[[1.123456, 2.123456], [3.987654, 2.123456], [3.987654, 4.5], [1.123456, 2.123456]]]}
    assert bbox(geom) == (1.1235, 2.1235, 3.9877, 4.5)
