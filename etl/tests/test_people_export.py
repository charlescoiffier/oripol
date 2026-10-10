from oripol_etl.export import pack_people


def test_names_are_deduplicated_in_a_table_and_referenced_by_index():
    packed = pack_people(
        {"COM-1": {"DVG": "Jean DUPONT", "LR": "Anne MARTIN"}, "COM-2": {"DVG": "Jean DUPONT"}}
    )
    names = packed["names"]
    assert sorted(names) == ["Anne MARTIN", "Jean DUPONT"]
    assert len(names) == 2
    t = packed["t"]
    assert [names[i] for i in t["COM-1"][1::2]] == ["Jean DUPONT", "Anne MARTIN"]
    assert t["COM-1"][0::2] == ["DVG", "LR"]
    assert t["COM-2"] == ["DVG", names.index("Jean DUPONT")]
