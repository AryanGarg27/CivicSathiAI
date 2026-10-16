from app.skill_loader import load_skill

def test_civic_skill_loads():
    skill = load_skill("skills/civic-request-intake")
    assert skill["name"] == "civic-request-intake"
    assert "resident" in skill["instructions"].lower()
