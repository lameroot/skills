"""SCIU 2 tests: help-with-time (injectable clock, present at all help levels, absent from JSON)."""
import json
import time

import clock
import run

FIXED_EPOCH = 1752880800.0  # deterministic; 2026-07-18-ish UTC


def test_clock_default_uses_real_now():
    clock.set_clock(None)
    before = time.time()
    line = clock.time_line()
    after = time.time()
    assert "Current time" in line
    ts = int(line.rsplit("Unix: ", 1)[1])
    assert before - 3 <= ts <= after + 3


def test_help_shows_injected_clock_at_all_levels(capsys):
    clock.set_clock(FIXED_EPOCH)
    try:
        for argv in (["--help"], ["schema", "--help"], ["schema", "get", "--help"]):
            capsys.readouterr()  # reset capture
            rc = run.main(argv)
            assert rc == 0
            out = capsys.readouterr().out
            assert "Current time (Europe/Moscow)" in out, f"missing time line in: {argv}"
            assert str(int(FIXED_EPOCH)) in out, f"missing fixed unix ts in: {argv}"
    finally:
        clock.set_clock(None)


def test_json_stdout_has_no_time_line(capsys):
    clock.set_clock(FIXED_EPOCH)
    try:
        rc = run.main(["schema", "get", "--json"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Current time" not in out
        payload = json.loads(out)
        assert payload["success"] is True
    finally:
        clock.set_clock(None)


def test_set_clock_freezes_and_releases():
    clock.set_clock(FIXED_EPOCH)
    assert clock.now_epoch() == FIXED_EPOCH
    clock.set_clock(None)
    assert clock.now_epoch() != FIXED_EPOCH
