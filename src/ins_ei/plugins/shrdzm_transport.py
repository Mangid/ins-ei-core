from __future__ import annotations

import socket
import struct


class ShrdzmTransport:
    """Read-only Modbus TCP transport for SHRDZM SMARTMETER firmware 1.3.x."""

    def __init__(self, host: str, port: int = 502, unit_id: int = 1, timeout: float = 5.0) -> None:
        self.host = host.strip()
        self.port = int(port)
        self.unit_id = int(unit_id)
        self.timeout = float(timeout)
        self._transaction_id = 0

    def _recv(self, sock: socket.socket, length: int) -> bytes:
        data = b""
        while len(data) < length:
            part = sock.recv(length - len(data))
            if not part:
                raise RuntimeError("SHRDZM_CONNECTION_CLOSED")
            data += part
        return data

    def read_registers(self, address: int, count: int) -> list[int]:
        self._transaction_id = (self._transaction_id + 1) & 0xFFFF or 1
        pdu = struct.pack(">BHH", 0x03, int(address), int(count))
        frame = struct.pack(">HHHB", self._transaction_id, 0, len(pdu) + 1, self.unit_id) + pdu
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.sendall(frame)
            header = self._recv(sock, 7)
            tid, protocol, length, unit = struct.unpack(">HHHB", header)
            if tid != self._transaction_id or protocol != 0 or unit != self.unit_id:
                raise RuntimeError("SHRDZM_MBAP")
            payload = self._recv(sock, length - 1)
        if not payload or payload[0] & 0x80:
            raise RuntimeError("SHRDZM_MODBUS_EXCEPTION")
        if payload[0] != 0x03 or payload[1] != count * 2:
            raise RuntimeError("SHRDZM_MODBUS_LENGTH")
        return list(struct.unpack(">" + ("H" * count), payload[2:]))

    @staticmethod
    def u32(words: list[int], index: int) -> int:
        return (words[index + 1] << 16) | words[index]

    @staticmethod
    def s32(words: list[int], index: int) -> int:
        return struct.unpack(">i", struct.pack(">HH", words[index + 1], words[index]))[0]

    def read_smartmeter(self) -> dict:
        registers = self.read_registers(0x0000, 27)
        if registers[0] == 0:
            raise RuntimeError("SHRDZM_DATA_INVALID")
        return {
            "valid": registers[0],
            "power_import_w": self.u32(registers, 1),
            "power_export_w": self.u32(registers, 3),
            "signed_power_w": self.s32(registers, 5),
            "import_energy_kwh": self.u32(registers, 7) / 1000.0,
            "export_energy_kwh": self.u32(registers, 9) / 1000.0,
            "voltage_l1_v": self.s32(registers, 11) / 1000.0,
            "voltage_l2_v": self.s32(registers, 13) / 1000.0,
            "voltage_l3_v": self.s32(registers, 15) / 1000.0,
            "current_l1_a": self.s32(registers, 17) / 1000.0,
            "current_l2_a": self.s32(registers, 19) / 1000.0,
            "current_l3_a": self.s32(registers, 21) / 1000.0,
            "reactive_power_import_var": self.u32(registers, 23),
            "reactive_power_export_var": self.u32(registers, 25),
        }
