import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import log_analyzer  # noqa: E402


def test_log_analyzer_summarises_fault_and_transitions(rig):
    rig.t += 1000
    rig.dut.tick(rig.t)
    result = log_analyzer.analyse(rig.dut.log)
    assert len(result["faults"]) == 1
    assert result["faults"][0]["detail"] == "SPEED_TIMEOUT"
    assert result["by_level"]["ERROR"] == 1
    assert result["transitions"]


def test_log_analyzer_ignores_malformed_lines():
    assert log_analyzer.analyse(["garbage", "", "t=5 INFO STATE A->B (x)"])["total"] == 1


def test_every_requirement_has_at_least_one_test():
    """Static traceability check: each requirement id appears in a test marker."""
    with open(ROOT / "requirements" / "requirements.csv") as fh:
        ids = [r["id"] for r in csv.DictReader(fh)]
    source = "".join(p.read_text() for p in (ROOT / "tests").glob("test_*.py"))
    missing = [i for i in ids if f'requirement("{i}")' not in source]
    assert not missing, f"requirements without tests: {missing}"
