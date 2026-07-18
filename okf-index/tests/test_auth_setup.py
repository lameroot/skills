"""SCIU 5 tests: auth setup/check/delete (dry-run/--yes, rollback, no leaks)."""
import json

import auth
import credentials
import run


class FakeKeyring:
    def __init__(self):
        self.store = {}
        self.fail_on = set()
        self.set_calls = []

    def get_password(self, s, a):
        return self.store.get((s, a))

    def set_password(self, s, a, v):
        self.set_calls.append(a)
        if a in self.fail_on:
            raise RuntimeError("boom")
        self.store[(s, a)] = v

    def delete_password(self, s, a):
        self.store.pop((s, a), None)


def _setup(monkeypatch, **fail):
    fake = FakeKeyring()
    fake.fail_on = set(fail.get("fail_on", ()))
    monkeypatch.setattr(credentials, "_real_keyring", fake)
    # ensure clean env so tests are deterministic
    for v in ("GEMINI_API_KEY", "OPENAI_API_KEY", "CONFLUENCE_USERNAME", "CONFLUENCE_API_TOKEN"):
        monkeypatch.delenv(v, raising=False)
    return fake


def test_dry_run_no_write(capsys, monkeypatch):
    fake = _setup(monkeypatch)
    rc = run.main(["auth", "setup", "--dry-run", "--json"])
    assert rc == 0
    assert fake.store == {}
    assert fake.set_calls == []
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["probe"].startswith("skipped")


def test_yes_writes_via_fake_keyring(capsys, monkeypatch):
    fake = _setup(monkeypatch)
    auth.set_setup_values({"CONFLUENCE_USERNAME": "alice", "CONFLUENCE_API_TOKEN": "tok-1"})
    try:
        rc = run.main(["auth", "setup", "--yes", "--json"])
    finally:
        auth.set_setup_values(None)
    assert rc == 0
    assert fake.store[("skills.okf-index", "CONFLUENCE_USERNAME")] == "alice"
    assert fake.store[("skills.okf-index", "CONFLUENCE_API_TOKEN")] == "tok-1"


def test_rollback_on_second_entry_failure(capsys, monkeypatch):
    fake = _setup(monkeypatch, fail_on={"CONFLUENCE_API_TOKEN"})
    auth.set_setup_values({"CONFLUENCE_USERNAME": "alice", "CONFLUENCE_API_TOKEN": "tok-1"})
    try:
        rc = run.main(["auth", "setup", "--yes", "--json"])
    finally:
        auth.set_setup_values(None)
    assert rc == 1  # failure
    captured = capsys.readouterr()
    failure = json.loads(captured.err)
    assert failure["success"] is False
    # USERNAME was written then rolled back
    assert ("skills.okf-index", "CONFLUENCE_USERNAME") not in fake.store


def test_setup_never_leaks_secret(capsys, monkeypatch):
    fake = _setup(monkeypatch)
    secret = "SETUP-SECRET-999"
    auth.set_setup_values({"CONFLUENCE_API_TOKEN": secret})
    try:
        run.main(["auth", "setup", "--yes", "--json"])
    finally:
        auth.set_setup_values(None)
    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err
    assert fake.store[("skills.okf-index", "CONFLUENCE_API_TOKEN")] == secret


def test_empty_value_not_stored(capsys, monkeypatch):
    fake = _setup(monkeypatch)
    auth.set_setup_values({"CONFLUENCE_API_TOKEN": ""})
    try:
        rc = run.main(["auth", "setup", "--yes", "--json"])
    finally:
        auth.set_setup_values(None)
    assert rc == 0
    assert fake.store == {}


def test_setup_requires_yes_or_dryrun(capsys, monkeypatch):
    _setup(monkeypatch)
    rc = run.main(["auth", "setup", "--json"])
    assert rc == 2


def test_check_reports_configured(capsys, monkeypatch):
    fake = _setup(monkeypatch)
    fake.store[("skills.okf-index", "CONFLUENCE_USERNAME")] = "bob"
    monkeypatch.setattr(credentials, "_real_keyring", fake)
    rc = run.main(["auth", "check", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert "CONFLUENCE_USERNAME" in payload["data"]["configured"]


def test_delete_removes_and_dryrun_noop(capsys, monkeypatch):
    fake = _setup(monkeypatch)
    fake.store[("skills.okf-index", "CONFLUENCE_API_TOKEN")] = "tok"
    monkeypatch.setattr(credentials, "_real_keyring", fake)
    # dry-run does not delete
    rc = run.main(["auth", "delete", "--dry-run", "--json"])
    assert rc == 0
    assert fake.store[("skills.okf-index", "CONFLUENCE_API_TOKEN")] == "tok"
    # --yes deletes
    rc = run.main(["auth", "delete", "--yes", "--json"])
    assert rc == 0
    assert ("skills.okf-index", "CONFLUENCE_API_TOKEN") not in fake.store
