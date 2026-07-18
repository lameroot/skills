"""SCIU 4 tests: auth status (redacted sources via fake keyring backend)."""
import json

import credentials
import run


class FakeKeyring:
    """In-memory keyring stand-in; never touches the OS keychain."""

    def __init__(self, store):
        self.store = store

    def get_password(self, service, account):
        return self.store.get((service, account))


def test_auth_status_never_prints_secrets(capsys, monkeypatch):
    planted = "SUPERSECRET-TOKEN-123"
    fake = FakeKeyring({("skills.okf-index", "CONFLUENCE_API_TOKEN"): planted})
    monkeypatch.setattr(credentials, "_real_keyring", fake)

    rc = run.main(["auth", "status", "--json"])
    assert rc == 0
    captured = capsys.readouterr()
    assert planted not in captured.out
    assert planted not in captured.err

    payload = json.loads(captured.out)
    assert payload["success"] is True
    creds = {c["account"]: c for c in payload["data"]["credentials"]}
    assert creds["CONFLUENCE_API_TOKEN"]["source"] == "keyring"
    assert creds["CONFLUENCE_API_TOKEN"]["configured"] is True


def test_reports_source_keyring_env_missing(capsys, monkeypatch):
    fake = FakeKeyring({("skills.okf-index", "GEMINI_API_KEY"): "kr"})  # keyring
    monkeypatch.setattr(credentials, "_real_keyring", fake)
    monkeypatch.setenv("OPENAI_API_KEY", "ENV-VALUE-456")  # environment

    rc = run.main(["auth", "status", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ENV-VALUE-456" not in out  # env value never leaked
    payload = json.loads(out)
    creds = {c["account"]: c for c in payload["data"]["credentials"]}
    assert creds["GEMINI_API_KEY"]["source"] == "keyring"
    assert creds["OPENAI_API_KEY"]["source"] == "environment"
    assert creds["CONFLUENCE_USERNAME"]["source"] == "missing"
    assert creds["CONFLUENCE_USERNAME"]["configured"] is False


def test_backend_name_reported(capsys, monkeypatch):
    class MyBackend:
        pass

    monkeypatch.setattr(credentials, "_real_keyring", MyBackend())
    rc = run.main(["auth", "status", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["data"]["backend"] == "MyBackend"


def test_unavailable_backend_reported(capsys, monkeypatch):
    monkeypatch.setattr(credentials, "_real_keyring", None)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CONFLUENCE_USERNAME", raising=False)
    monkeypatch.delenv("CONFLUENCE_API_TOKEN", raising=False)
    rc = run.main(["auth", "status", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["data"]["backend"] == "unavailable"
    # everything missing, nothing configured
    assert all(c["source"] == "missing" for c in payload["data"]["credentials"])
