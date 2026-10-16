from pathlib import Path
import re

class SkillLoadError(ValueError):
    pass

def load_skill(skill_dir: str | Path) -> dict:
    """Load basic Agent Skills frontmatter and instructions without executing content."""
    path = Path(skill_dir) / "SKILL.md"
    if not path.is_file():
        raise SkillLoadError(f"Missing skill file: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise SkillLoadError("SKILL.md must start with YAML frontmatter")
    parts = text.split("---", 2)
    if len(parts) != 3:
        raise SkillLoadError("Invalid SKILL.md frontmatter delimiters")
    frontmatter, instructions = parts[1], parts[2].strip()
    name_match = re.search(r"(?m)^name:\s*([a-z0-9-]+)\s*$", frontmatter)
    desc_match = re.search(r"(?m)^description:\s*(.+)\s*$", frontmatter)
    if not name_match or not desc_match:
        raise SkillLoadError("Skill requires name and description metadata")
    directory_name = Path(skill_dir).name
    if name_match.group(1) != directory_name:
        raise SkillLoadError("Skill name must match the containing directory name")
    if not instructions:
        raise SkillLoadError("Skill instructions are empty")
    return {"name": name_match.group(1), "description": desc_match.group(1), "instructions": instructions}
