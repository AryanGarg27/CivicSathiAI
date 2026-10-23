import pytest


@pytest.fixture(autouse=True)
def isolate_audit(tmp_path, monkeypatch):
    monkeypatch.setenv('AUDIT_LOG_PATH', str(tmp_path / 'audit.jsonl'))
