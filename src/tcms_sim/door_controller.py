"""Simulated train door controller - the device under test (DUT).

Requirements implemented (see requirements/requirements.csv):
  REQ-DOOR-001  Doors shall not open while speed > 5.0 km/h.
  REQ-DOOR-002  If an obstacle is detected while closing, doors shall reopen.
  REQ-DOOR-003  3 consecutive invalid (CRC) frames shall put the controller in FAULT.
  REQ-DOOR-004  No valid speed frame for > 500 ms shall put the controller in FAULT.
  REQ-DOOR-005  Unknown command values shall be rejected without a state change.
  REQ-DOOR-006  Door state transitions shall follow the specified state machine.
"""
from enum import Enum

from .can_bus import DOOR_CMD_ID, SPEED_ID, Frame

SPEED_LIMIT_KMH = 5.0
SPEED_TIMEOUT_MS = 500
MAX_BAD_FRAMES = 3
TRAVEL_MS = 1000

CMD_NONE, CMD_OPEN, CMD_CLOSE = 0, 1, 2


class DoorState(Enum):
    CLOSED_LOCKED = "CLOSED_LOCKED"
    OPENING = "OPENING"
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    FAULT = "FAULT"


class DoorController:
    def __init__(self) -> None:
        self.state = DoorState.CLOSED_LOCKED
        self.speed_kmh = 0.0
        self.bad_frames = 0
        self.now_ms = 0
        self.last_speed_ms = 0
        self._move_start_ms = 0
        self.log: list[str] = []

    # ---- logging -------------------------------------------------------
    def _log(self, level: str, event: str, detail: str = "") -> None:
        self.log.append(f"t={self.now_ms} {level} {event} {detail}".rstrip())

    def _set_state(self, new: DoorState, reason: str) -> None:
        self._log("INFO", "STATE", f"{self.state.value}->{new.value} ({reason})")
        self.state = new
        self._move_start_ms = self.now_ms

    def _fault(self, reason: str) -> None:
        if self.state is not DoorState.FAULT:
            self._log("ERROR", "FAULT", reason)
            self._set_state(DoorState.FAULT, reason)

    # ---- inputs --------------------------------------------------------
    def receive(self, frame: Frame) -> None:
        self.now_ms = max(self.now_ms, frame.timestamp_ms)
        if not frame.is_valid():
            self.bad_frames += 1
            self._log("WARN", "BAD_CRC", f"id=0x{frame.can_id:X} count={self.bad_frames}")
            if self.bad_frames >= MAX_BAD_FRAMES:
                self._fault("CRC_ERRORS")
            return
        self.bad_frames = 0
        if frame.can_id == SPEED_ID:
            self.speed_kmh = int.from_bytes(frame.data[:2], "big") / 10.0
            self.last_speed_ms = frame.timestamp_ms
        elif frame.can_id == DOOR_CMD_ID:
            self._handle_command(frame.data[0], frame.data[1])

    def _handle_command(self, cmd: int, obstacle: int) -> None:
        if self.state is DoorState.FAULT:
            self._log("WARN", "CMD_IGNORED", "controller in FAULT")
            return
        if cmd not in (CMD_NONE, CMD_OPEN, CMD_CLOSE):
            self._log("WARN", "CMD_REJECTED", f"unknown cmd={cmd}")
            return
        if self.state is DoorState.CLOSING and obstacle:
            self._set_state(DoorState.OPENING, "obstacle")
            return
        if cmd == CMD_OPEN and self.state is DoorState.CLOSED_LOCKED:
            if self.speed_kmh > SPEED_LIMIT_KMH:
                self._log("WARN", "OPEN_DENIED", f"speed={self.speed_kmh}")
                return
            self._set_state(DoorState.OPENING, "open cmd")
        elif cmd == CMD_CLOSE and self.state is DoorState.OPEN:
            self._set_state(DoorState.CLOSING, "close cmd")

    # ---- time ----------------------------------------------------------
    def tick(self, now_ms: int) -> None:
        self.now_ms = now_ms
        if self.state is not DoorState.FAULT and now_ms - self.last_speed_ms > SPEED_TIMEOUT_MS:
            self._fault("SPEED_TIMEOUT")
            return
        elapsed = now_ms - self._move_start_ms
        if self.state is DoorState.OPENING and elapsed >= TRAVEL_MS:
            self._set_state(DoorState.OPEN, "travel complete")
        elif self.state is DoorState.CLOSING and elapsed >= TRAVEL_MS:
            self._set_state(DoorState.CLOSED_LOCKED, "travel complete")

    def reset(self) -> bool:
        """Clear FAULT only when the train is stationary."""
        if self.state is DoorState.FAULT and self.speed_kmh == 0.0:
            self.bad_frames = 0
            self.last_speed_ms = self.now_ms
            self._set_state(DoorState.CLOSED_LOCKED, "reset")
            return True
        return False
