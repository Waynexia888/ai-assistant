from pathlib import Path
import re


SKILL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class SkillLoader:
    def __init__(self, skills_dir: Path | None = None) -> None:
        self.skills_dir = skills_dir or Path(__file__).resolve().parent

    def load(self, skill_name: str) -> str:
        if not SKILL_NAME_PATTERN.fullmatch(skill_name):
            return ""

        path = self.skills_dir / skill_name / "SKILL.md"

        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""
