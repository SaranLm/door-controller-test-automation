"""Functional, boundary-value, equivalence-class, negative and state-transition tests."""
import pytest

from tcms_sim.door_controller import CMD_CLOSE, DoorState, SPEED_LIMIT_KMH


# ---- REQ-DOOR-001: boundary-value analysis around the 5.0 km/h limit ------
@pytest.mark.requirement("REQ-DOOR-001")
@pytest.mark.technique("boundary-value")
@pytest.mark.parametrize("speed, expected", [
    (0.0, DoorState.OPENING),
    (4.9, DoorState.OPENING),
    (SPEED_LIMIT_KMH, DoorState.OPENING),      # limit itself is allowed (> 5.0 is denied)
    (5.1, DoorState.CLOSED_LOCKED),
    (5.2, DoorState.CLOSED_LOCKED),
])
def test_open_command_at_speed_boundary(rig, speed, expected):
    rig.send_speed(speed)
    rig.open()
    assert rig.dut.state is expected


# ---- REQ-DOOR-001: equivalence classes (stationary / low / high speed) -----
@pytest.mark.requirement("REQ-DOOR-001")
@pytest.mark.technique("equivalence-class")
@pytest.mark.parametrize("speed, may_open", [(0.0, True), (2.5, True), (60.0, False), (120.0, False)])
def test_open_command_equivalence_classes(rig, speed, may_open):
    rig.send_speed(speed)
    rig.open()
    assert (rig.dut.state is DoorState.OPENING) is may_open


@pytest.mark.requirement("REQ-DOOR-001")
@pytest.mark.technique("negative")
def test_open_denied_is_logged(rig):
    rig.send_speed(40.0)
    rig.open()
    assert any("OPEN_DENIED" in line for line in rig.dut.log)


# ---- REQ-DOOR-006: state-transition testing -------------------------------
@pytest.mark.requirement("REQ-DOOR-006")
@pytest.mark.technique("state-transition")
def test_full_open_close_cycle(rig):
    assert rig.dut.state is DoorState.CLOSED_LOCKED
    rig.open()
    assert rig.dut.state is DoorState.OPENING
    rig.advance(999)
    assert rig.dut.state is DoorState.OPENING       # travel not yet complete
    rig.advance(1)
    assert rig.dut.state is DoorState.OPEN
    rig.close()
    assert rig.dut.state is DoorState.CLOSING
    rig.advance(1000)
    assert rig.dut.state is DoorState.CLOSED_LOCKED


@pytest.mark.requirement("REQ-DOOR-006")
@pytest.mark.technique("state-transition")
def test_close_command_ignored_when_already_closed(rig):
    rig.close()
    assert rig.dut.state is DoorState.CLOSED_LOCKED


@pytest.mark.requirement("REQ-DOOR-006")
@pytest.mark.technique("state-transition")
def test_open_command_ignored_while_already_open(rig):
    rig.open_fully()
    rig.open()
    assert rig.dut.state is DoorState.OPEN


# ---- REQ-DOOR-002: obstacle handling --------------------------------------
@pytest.mark.requirement("REQ-DOOR-002")
@pytest.mark.technique("state-transition")
def test_obstacle_while_closing_reopens(rig):
    rig.open_fully()
    rig.close()
    rig.advance(300)
    rig.send_cmd(CMD_CLOSE, obstacle=1)
    assert rig.dut.state is DoorState.OPENING


@pytest.mark.requirement("REQ-DOOR-002")
@pytest.mark.technique("negative")
def test_obstacle_flag_ignored_when_not_closing(rig):
    rig.send_cmd(0, obstacle=1)
    assert rig.dut.state is DoorState.CLOSED_LOCKED


# ---- REQ-DOOR-005: negative testing of invalid command values -------------
@pytest.mark.requirement("REQ-DOOR-005")
@pytest.mark.technique("negative")
@pytest.mark.parametrize("cmd", [3, 7, 128, 255])
def test_unknown_command_rejected_without_state_change(rig, cmd):
    rig.send_cmd(cmd)
    assert rig.dut.state is DoorState.CLOSED_LOCKED
    assert any("CMD_REJECTED" in line for line in rig.dut.log)
