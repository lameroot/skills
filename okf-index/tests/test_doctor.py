"""SCIU 6 tests: doctor (atomic, redacted, semantic exit codes, probes skipped)."""
import json

import credentials
import doctor
import run


class FakeKeyring:
    def __init__(self, store=None):
        self.store = dict(store or {})
        self.set_calls = []

    def get_password(self, s, a):
        return self.store.get((s, a))

    def set_password(self, s, a, v):
        self.set_calls.append(a)
        self.store[(s, a)] = v

    def delete_password(self, s, a):
        self.store.pop((s, a), None)


def test_doctor_redacts_values(capsys, monkeypatch):
    secret = "DOCTOR-SECRET-7"
    fake = FakeKeyring({("skills.okf-index", "CONFLUENCE_API_TOKEN"): secret})
    monkeypatch.setattr(credentials, "_real_keyring", fake)
    rc = run.main(["doctor", "--json"])
    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err
    assert rc == 0


def test_doctor_no_writes_no_prompts(monkeypatch):
    fake = FakeKeyring()
    monkeypatch.setattr(credentials, "_real_keyring", fake)
    run.main(["doctor", "--json"])
    assert fake.set_calls == []
    assert fake.store == {}


def test_probes_skipped_when_not_configured(capsys, monkeypatch):
    monkeypatch.setattr(credentials, "_real_keyring", None)
    rc = run.main(["doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["data"]["probe"].startswith("skipped")
    assert payload["data"]["backend"] == "unavailable"


def test_missing_required_nonsecret_exit2_guidance():
    cfg = {
        "keyring_service": "skills.okf-index",
        "settings": [
            {
                "name": "FOO",
                "type": "string",
                "required": True,
                "credential": False,
                "help": {"source": "ask admin", "instructions": ["set FOO"]},
            }
        ],
    }
    result = doctor.doctor_check(cfg, env={}, keyring_backend=None)
    assert result["exit_code"] == 2
    assert result["ok"] is False
    assert result["missing_required"][0]["name"] == "FOO"
    assert result["missing_required"][0]["help"]["source"] == "ask admin"


def test_invalid_manifest_exit2():
    cfg = {"keyring_service": "x", "settings": [{"name": "FOO"}]}  # missing 'type'
    result = doctor.doctor_check(cfg, env={}, keyring_backend=None)
    assert result["exit_code"] == 2
    assert result["issues"]


def test_valid_config_exit0(capsys, monkeypatch):
    monkeypatch.setattr(credentials, "_real_keyring", FakeKeyring())
    rc = run.main(["doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["data"]["ok"] is True
    names = {r["name"] for r in payload["data"]["settings"]}
    assert "OKF_VAULT_PATH" in names
