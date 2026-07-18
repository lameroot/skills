"""SCIU 3 tests: settings.json manifest + loader (non-secret resolution)."""
import os

import pytest

import settings
from settings import SettingsConfigError, load_settings_config, resolve_runtime_settings


def test_manifest_is_valid_json_and_has_keyring_service():
    cfg = load_settings_config()
    assert cfg["skill"] == "okf-index"
    assert cfg["keyring_service"] == "skills.okf-index"
    assert isinstance(cfg["settings"], list) and cfg["settings"]


def test_credential_entries_have_no_default():
    cfg = load_settings_config()
    for item in cfg["settings"]:
        if item.get("credential"):
            assert "default" not in item, f"credential {item['name']} must not carry a default"


def test_env_overrides_nonsecret_default_only():
    cfg = load_settings_config()
    values, sources = resolve_runtime_settings(cfg, env={"OKF_VAULT_PATH": "/tmp/x"})
    assert values["OKF_VAULT_PATH"] == "/tmp/x"
    assert sources["OKF_VAULT_PATH"] == "environment"
    # a non-overridden non-secret falls back to default
    assert sources["OKF_ENRICH_PROVIDER"] == "default"
    assert values["OKF_ENRICH_PROVIDER"] == "gemini"


def test_types_validated():
    cfg = load_settings_config()
    values, _ = resolve_runtime_settings(
        cfg, env={"OKF_INDEX_AUTO_CONFIRM": "yes", "OKF_BODY_MAX_BYTES": "123"}
    )
    assert values["OKF_INDEX_AUTO_CONFIRM"] is True
    assert values["OKF_BODY_MAX_BYTES"] == 123
    with pytest.raises(SettingsConfigError):
        resolve_runtime_settings(cfg, env={"OKF_INDEX_AUTO_CONFIRM": "not-a-bool"})
    with pytest.raises(SettingsConfigError):
        resolve_runtime_settings(cfg, env={"OKF_BODY_MAX_BYTES": "abc"})


def test_missing_required_nonsecret_reported_missing():
    cfg = load_settings_config()
    # craft a required non-secret with no env/default
    cfg2 = {"settings": [{"name": "FOO", "type": "string", "required": True, "credential": False}]}
    _, sources = resolve_runtime_settings(cfg2, env={})
    assert sources["FOO"] == "missing"


def test_apply_defaults_to_environ_sets_nonsecret_only():
    cfg = load_settings_config()
    env = {}
    settings.apply_defaults_to_environ(cfg, env=env)
    assert env.get("OKF_VAULT_PATH") == "~/okf-vault"
    assert env.get("OKF_ENRICH_PROVIDER") == "gemini"
    # credentials are NEVER seeded into env
    for cred in ("GEMINI_API_KEY", "OPENAI_API_KEY", "CONFLUENCE_USERNAME", "CONFLUENCE_API_TOKEN"):
        assert cred not in env
