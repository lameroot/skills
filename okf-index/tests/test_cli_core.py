"""SCIU 1 tests: CLI core — schema get, JSON envelope, exit codes, error bridge."""
import argparse
import io
import json

import run
from envelope import emit_success, emit_error
from errors import SkillError, UsageError, NotFoundError, PermissionDeniedError, ConflictError


def test_schema_get_returns_valid_json(capsys):
    rc = run.main(["schema", "get", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)  # raises if not valid JSON
    assert payload["success"] is True
    data = payload["data"]
    assert data["skill"] == "okf-index"
    assert "version" in data
    assert isinstance(data["commands"], list) and data["commands"]
    assert "schema" in {c["resource"] for c in data["commands"]}


def test_unknown_command_exits_2(capsys):
    rc = run.main(["bogus-resource"])
    assert rc == 2
    assert capsys.readouterr().err  # argparse diagnostic preserved on stderr


def test_unknown_flag_exits_2_with_hint(capsys):
    rc = run.main(["schema", "get", "--nope-not-a-flag"])
    assert rc == 2
    assert capsys.readouterr().err  # hint/diagnostic present


def test_success_envelope_stdout_error_stderr():
    out, err = io.StringIO(), io.StringIO()
    emit_success({"x": 1}, out)
    emit_error("usage", "bad input", err, hint="see --help")
    success = json.loads(out.getvalue())
    failure = json.loads(err.getvalue())
    assert success["success"] is True and success["data"]["x"] == 1
    assert failure["success"] is False
    assert failure["error"]["code"] == "usage"
    assert failure["error"]["message"] == "bad input"
    assert failure["error"]["hint"] == "see --help"
    assert failure["error"]["retriable"] is False


def test_error_classes_carry_exit_codes():
    assert UsageError("u").exit_code == 2
    assert NotFoundError("n").exit_code == 3
    assert PermissionDeniedError("p").exit_code == 4
    assert ConflictError("c").exit_code == 5
    e = UsageError("u", code="mycode", hint="h")
    assert isinstance(e, SkillError)
    assert e.code == "mycode" and e.hint == "h"


def test_skill_error_bridge_emits_structured_stderr(capsys):
    """A handler raising SkillError -> structured JSON on stderr + semantic exit code."""
    def boom(args, out, err):
        raise NotFoundError("missing thing", hint="try something else")

    key = ("__test__", "boom")
    run.HANDLERS[key] = boom
    try:
        ns = argparse.Namespace(resource="__test__", action="boom", json=True)
        rc = run._execute(ns)
    finally:
        run.HANDLERS.pop(key, None)
    assert rc == 3
    failure = json.loads(capsys.readouterr().err)
    assert failure["success"] is False
    assert failure["error"]["code"] == "not_found"
    assert failure["error"]["hint"] == "try something else"
