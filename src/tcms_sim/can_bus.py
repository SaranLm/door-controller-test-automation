"""Minimal CAN-style frame model with CRC-8 and a fault injector.

This is a *simulation* used to practise verification & validation techniques.
It is not a real vehicle bus implementation.
"""
from dataclasses import dataclass, replace

SPEED_ID = 0x100        # vehicle speed, uint16 big-endian, 0.1 km/h units
DOOR_CMD_ID = 0x200     # data[0]: 0 none, 1 open, 2 close; data[1]: obstacle flag


def crc8(data: bytes, poly: int = 0x07) -> int:
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ poly) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


@dataclass(frozen=True)
class Frame:
    can_id: int
    data: bytes
    crc: int
    timestamp_ms: int = 0

    @classmethod
    def build(cls, can_id: int, data, timestamp_ms: int = 0) -> "Frame":
        payload = bytes(data)
        return cls(can_id, payload, crc8(bytes([can_id & 0xFF]) + payload), timestamp_ms)

    def is_valid(self) -> bool:
        return self.crc == crc8(bytes([self.can_id & 0xFF]) + self.data)


def speed_frame(kmh: float, timestamp_ms: int) -> Frame:
    raw = int(round(kmh * 10))
    if not 0 <= raw <= 0xFFFF:
        raise ValueError("speed out of encodable range")
    return Frame.build(SPEED_ID, raw.to_bytes(2, "big"), timestamp_ms)


def door_cmd_frame(cmd: int, obstacle: int, timestamp_ms: int) -> Frame:
    return Frame.build(DOOR_CMD_ID, [cmd, obstacle], timestamp_ms)


class FaultInjector:
    """Helpers that turn a good frame into a faulty one (fault-injection tests)."""

    @staticmethod
    def corrupt(frame: Frame, bit: int = 0) -> Frame:
        data = bytearray(frame.data)
        data[0] ^= 1 << (bit % 8)
        return replace(frame, data=bytes(data))   # CRC left unchanged -> invalid

    @staticmethod
    def bad_crc(frame: Frame) -> Frame:
        return replace(frame, crc=(frame.crc ^ 0xFF) & 0xFF)
