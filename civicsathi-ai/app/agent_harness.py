from app.model_adapter import OllamaModelAdapter
from app.schemas import CivicRequest
from app.skill_loader import load_skill
from app.permissions import authorize_tool

class CivicRequestHarness:
    def __init__(self, model_adapter: OllamaModelAdapter, services: list[dict], skill_dir: str = "skills/civic-request-intake"):
        self.model_adapter = model_adapter
        self.services = services
        self.skill = load_skill(skill_dir)

    def intake(self, request_text: str, language: str, location: str = "") -> CivicRequest:
        if not request_text or not request_text.strip():
            raise ValueError("Request text cannot be empty")
        # Skill instructions are passed as context, never executed as code.
        return self.model_adapter.analyze(
            request_text=("SKILL INSTRUCTIONS:\n" + self.skill["instructions"] + "\n\nRESIDENT REQUEST:\n" + request_text.strip()),
            language=language,
            location=location.strip(),
            services=self.services,
        )

    def authorize_action(self, action: str, *, explicitly_authorized: bool = False) -> None:
        """Permission gate for any future tool action; live actions fail closed by default."""
        authorize_tool(action, explicitly_authorized=explicitly_authorized)
