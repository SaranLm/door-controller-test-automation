# TCMS-Style Test Automation Framework (Simulation)

A Python/pytest project that practises **verification & validation** of safety-related embedded software.
It tests a *simulated* train door controller (the device under test) that communicates through CAN-style
frames protected by a CRC-8. It is a learning/portfolio project and does not implement a real vehicle bus
or any railway standard.

## What it demonstrates
- **Requirements traceability** - `requirements/requirements.csv` lists 6 requirements; every test is tagged
  with `@pytest.mark.requirement("REQ-DOOR-00x")`. A test fails if a requirement has no test.
- **Test-design techniques** - boundary-value, equivalence-class, negative, state-transition, fault-injection
  (each test is tagged with `@pytest.mark.technique(...)`).
- **Fault injection** - corrupted frames, bad CRCs, dropped speed signal, signal-timeout boundary (500 ms).
- **Reporting** - after each run, `reports/traceability.csv` and `reports/verification_status.md` are
  generated, including defect-report drafts for any failing test.
- **Log analysis** - `tools/log_analyzer.py` summarises faults and state-transition history from DUT logs.
- **Regression in CI** - `.github/workflows/ci.yml` runs the suite on every push.

## Run it
```bash
pip install pytest
pytest                      # 34 tests
cat reports/verification_status.md
```

## Layout
```
src/tcms_sim/can_bus.py          frames, CRC-8, fault injector
src/tcms_sim/door_controller.py  DUT: door state machine + requirements
tests/                           functional + fault-injection + tooling tests
tools/log_analyzer.py            log summariser
requirements/requirements.csv    requirement list used for traceability
```

## Ideas to extend (good interview talking points)
- Add a second DUT (e.g. traction-interlock or brake-status signal) with new requirements.
- Replace the in-memory bus with `python-can`'s virtual interface.
- Add a deliberately injected bug to the DUT and show the defect report the suite generates.
