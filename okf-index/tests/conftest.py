import sys
from pathlib import Path

# Make scripts/ importable for tests (mirrors run.py's own sys.path fallback).
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
