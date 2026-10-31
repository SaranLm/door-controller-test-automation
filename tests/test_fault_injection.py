"""Fault-injection and robustness tests: corrupted frames and lost signals."""
import pytest

from tcms_sim.can_bus import FaultInjector, door_cmd_frame, speed_frame
from tcms_sim.door_controller import CMD_OPEN, DoorState, MAX_BAD_FRAMES, SPEED_TIMEOUT_MS


@pytest.mark.requirement("REQ-DOOR-003")
@pytest.mark.technique("fault-injection")
def test_single_corrupted_frame_is_tolerated(rig):
    rig.dut.receive(FaultInjector.corrupt(speed_frame(0.0, rig.t)))
    assert rig.dut.state is DoorState.CLOSED_LOCKED
    assert rig.dut.bad_frames == 1


@pytest.mark.requirement("REQ-DOOR-003")
@pytest.mark.technique("fault-injection")
def test_consecutive_bad_frames_cause_fault(rig):
    for _ in range(MAX_BAD_FRAMES):
        rig.dut.receive(FaultInjector.bad_crc(speed_frame(0.0, rig.t)))
    assert rig.dut.state is DoorState.FAULT


@pytest.mark.requirement("REQ-DOOR-003")
@pytest.mark.technique("boundary-value")
def test_one_below_threshold_does_not_fault(rig):
    for _ in range(MAX_BAD_FRAMES - 1):
        rig.dut.receive(FaultInjector.bad_crc(speed_frame(0.0, rig.t)))
    assert rig.dut.state is not DoorState.FAULT


@pytest.mark.requirement("REQ-DOOR-003")
@pytest.mark.technique("fault-injection")
def test_valid_frame_resets_bad_frame_counter(rig):
    for _ in range(MAX_BAD_FRAMES - 1):
        rig.dut.receive(FaultInjector.corrupt(door_cmd_frame(0, 0, rig.t)))
    rig.send_speed(0.0)                       # good frame clears the count
    rig.dut.receive(FaultInjector.corrupt(door_cmd_frame(0, 0, rig.t)))
    assert rig.dut.state is not DoorState.FAULT


@pytest.mark.requirement("REQ-DOOR-003")
@pytest.mark.technique("negative")
def test_corrupted_open_command_is_not_executed(rig):
    rig.dut.receive(FaultInjector.corrupt(door_cmd_frame(CMD_OPEN, 0, rig.t)))
    assert rig.dut.state is DoorState.CLOSED_LOCKED


# ---- REQ-DOOR-004: signal loss (boundary at 500 ms) -----------------------
@pytest.mark.requirement("REQ-DOOR-004")
@pytest.mark.technique("boundary-value")
@pytest.mark.parametrize("silence_ms, faulted", [
    (SPEED_TIMEOUT_MS - 1, False),
    (SPEED_TIMEOUT_MS, False),
    (SPEED_TIMEOUT_MS + 1, True),
    (2000, True),
])
def test_speed_signal_timeout_boundary(rig, silence_ms, faulted):
    rig.t += silence_ms
    rig.dut.tick(rig.t)
    assert (rig.dut.state is DoorState.FAULT) is faulted


@pytest.mark.requirement("REQ-DOOR-004")
@pytest.mark.technique("fault-injection")
def test_dropped_speed_frames_during_door_travel_cause_fault(rig):
    rig.open()
    rig.advance(600, keepalive=False)         # speed frames dropped on the bus
    assert rig.dut.state is DoorState.FAULT


@pytest.mark.requirement("REQ-DOOR-006")
@pytest.mark.technique("negative")
def test_commands_ignored_in_fault_until_reset(rig):
    rig.t += 1000
    rig.dut.tick(rig.t)
    rig.send_speed(0.0)
    rig.open()
    assert rig.dut.state is DoorState.FAULT
    assert rig.dut.reset() is True
    rig.open()
    assert rig.dut.state is DoorState.OPENING


@pytest.mark.requirement("REQ-DOOR-006")
@pytest.mark.technique("negative")
def test_reset_refused_while_moving(rig):
    rig.t += 1000
    rig.dut.tick(rig.t)
    rig.send_speed(30.0)
    assert rig.dut.reset() is False
    assert rig.dut.state is DoorState.FAULT
