"""SCIU 4 tests: auth status (redacted sources via fake keyring backend)."""
import json

import credentials
import run


class FakeKeyring:
    def __init__(self, store=None):
        self.store = dict(store or {})

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
    fake = FakeKeyring({("skills.okf-index", "ENRICH_API_KEY"): "kr"})
    monkeypatch.setattr(credentials, "_real_keyring", fake)
    monkeypatch.setenv("CONFLUENCE_API_TOKEN", "ENV-VALUE-456")
    rc = run.main(["auth", "status", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ENV-VALUE-456" not in out
    payload = json.loads(out)
    creds = {c["account"]: c for c in payload["data"]["credentials"]}
    assert creds["ENRICH_API_KEY"]["source"] == "keyring"
    assert creds["CONFLUENCE_API_TOKEN"]["source"] == "environment"


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
    for v in ("ENRICH_API_KEY", "CONFLUENCE_API_TOKEN"):
        monkeypatch.delenv(v, raising=False)
    rc = run.main(["auth", "status", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["data"]["backend"] == "unavailable"
    assert all(c["source"] == "missing" for c in payload["data"]["credentials"])
