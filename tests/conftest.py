"""Shared fixtures + a small plugin that produces a requirements traceability report."""
import csv
from pathlib import Path

import pytest

from tcms_sim.can_bus import door_cmd_frame, speed_frame
from tcms_sim.door_controller import CMD_CLOSE, CMD_NONE, CMD_OPEN, DoorController

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reports"
_results: list[dict] = []


class Rig:
    """Test bench wrapper: drives the DUT with frames and simulated time."""

    def __init__(self) -> None:
        self.dut = DoorController()
        self.t = 0
        self.speed = 0.0

    def send_speed(self, kmh: float) -> None:
        self.speed = kmh
        self.dut.receive(speed_frame(kmh, self.t))

    def send_cmd(self, cmd: int, obstacle: int = 0) -> None:
        self.dut.receive(door_cmd_frame(cmd, obstacle, self.t))

    def open(self) -> None:
        self.send_cmd(CMD_OPEN)

    def close(self) -> None:
        self.send_cmd(CMD_CLOSE)

    def idle(self) -> None:
        self.send_cmd(CMD_NONE)

    def advance(self, ms: int, keepalive: bool = True) -> None:
        """Advance time in 100 ms steps, optionally refreshing the speed signal."""
        end = self.t + ms
        while self.t < end:
            self.t = min(self.t + 100, end)
            if keepalive:
                self.send_speed(self.speed)
            self.dut.tick(self.t)

    def open_fully(self) -> None:
        self.open()
        self.advance(1000)


@pytest.fixture
def rig() -> Rig:
    r = Rig()
    r.send_speed(0.0)
    return r


def pytest_configure(config):
    config.addinivalue_line("markers", "requirement(id): requirement this test verifies")
    config.addinivalue_line("markers", "technique(name): test-design technique used")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when != "call":
        return
    req = item.get_closest_marker("requirement")
    tech = item.get_closest_marker("technique")
    _results.append({
        "requirement": req.args[0] if req else "",
        "technique": tech.args[0] if tech else "",
        "test": item.nodeid,
        "outcome": rep.outcome,
        "detail": str(rep.longrepr).splitlines()[-1] if rep.failed else "",
    })


def pytest_sessionfinish(session, exitstatus):
    if not _results:
        return
    REPORT_DIR.mkdir(exist_ok=True)
    with open(REPORT_DIR / "traceability.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["requirement", "technique", "test", "outcome", "detail"])
        w.writeheader()
        w.writerows(sorted(_results, key=lambda r: (r["requirement"], r["test"])))
    with open(ROOT / "requirements" / "requirements.csv") as fh:
        reqs = [r["id"] for r in csv.DictReader(fh)]
    lines = ["# Verification status", "", "| Requirement | Tests | Passed | Failed | Status |", "|---|---|---|---|---|"]
    for rid in reqs:
        rows = [r for r in _results if r["requirement"] == rid]
        passed = sum(r["outcome"] == "passed" for r in rows)
        failed = sum(r["outcome"] == "failed" for r in rows)
        status = "NOT COVERED" if not rows else ("FAIL" if failed else "PASS")
        lines.append(f"| {rid} | {len(rows)} | {passed} | {failed} | {status} |")
    failures = [r for r in _results if r["outcome"] == "failed"]
    if failures:
        lines += ["", "## Defect report drafts", ""]
        for i, r in enumerate(failures, 1):
            lines += [f"### DEFECT-{i:03d}: {r['test']}", f"- Requirement: {r['requirement']}",
                      f"- Technique: {r['technique']}", f"- Observed: {r['detail']}",
                      "- Steps to reproduce: run `pytest " + r["test"] + "`", ""]
    (REPORT_DIR / "verification_status.md").write_text("\n".join(lines) + "\n")
