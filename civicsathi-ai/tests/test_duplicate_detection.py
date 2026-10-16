from app.duplicate_detection import find_possible_duplicates

def test_potential_match_is_only_suggested():
    matches = find_possible_duplicates("Garbage accumulated near park; collection delayed", [{"id":"SAMPLE-1", "summary":"Garbage has accumulated near a public park and waste collection has been delayed."}])
    assert matches
    assert matches[0]["id"] == "SAMPLE-1"
