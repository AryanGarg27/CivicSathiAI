import json
from datetime import datetime, timezone
from pathlib import Path

class AuditLog:
    """Append minimal workflow events; do not pass raw complaint text or personal data."""
    def __init__(self, path: str = "local_audit.jsonl"):
        self.path = Path(path)

    def record(self, event: str, details: dict) -> None:
        record = {"time": datetime.now(timezone.utc).isoformat(), "event": event, "details": details}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
