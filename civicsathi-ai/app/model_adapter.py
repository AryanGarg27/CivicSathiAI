import json
import requests
from app.schemas import CivicRequest

class ModelUnavailable(RuntimeError):
    """Raised when the configured open-weight model cannot be reached or used."""

class OllamaModelAdapter:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:3b", timeout: int = 90):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def analyze(self, request_text: str, language: str, location: str, services: list[dict]) -> CivicRequest:
        schema = CivicRequest.model_json_schema()
        system = (
            "You are a civic request intake assistant for an independent prototype. "
            "Return only JSON that matches the supplied schema. Use the provided service catalogue. "
            "Do not invent case IDs, official status, department responses, or claim a complaint was submitted. "
            "If uncertain, lower confidence and set needs_human_review=true. Never reject a complaint. "
            "The user must review the draft."
        )
        payload = {
            "request": request_text,
            "preferred_language": language,
            "resident_supplied_location": location or None,
            "known_services": services,
            "output_schema": schema,
        }
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "stream": False, "format": schema,
                      "messages": [{"role": "system", "content": system},
                                   {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]},
                timeout=self.timeout,
            )
            if response.status_code == 404:
                raise ModelUnavailable(f"Model '{self.model}' may not be pulled. Run: ollama pull {self.model}")
            response.raise_for_status()
            content = response.json().get("message", {}).get("content", "")
            parsed = json.loads(content)
            # Prefer resident-supplied location when one was given.
            if location and not parsed.get("location"):
                parsed["location"] = location
            return CivicRequest.model_validate(parsed)
        except ModelUnavailable:
            raise
        except requests.RequestException as exc:
            raise ModelUnavailable(f"Could not connect to Ollama at {self.base_url}: {exc}") from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise ModelUnavailable(f"Model returned invalid structured output: {exc}") from exc
