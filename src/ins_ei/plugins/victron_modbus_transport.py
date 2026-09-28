from __future__ import annotations

import socket
import struct


class VictronModbusTransport:
    """Minimal read-only Modbus TCP transport for a Victron GX gateway."""

    def __init__(self, host: str, port: int = 502, timeout: float = 5.0) -> None:
        self.host = host.strip()
        self.port = int(port)
        self.timeout = float(timeout)
        self._transaction_id = 0

    def _recv(self, sock: socket.socket, length: int) -> bytes:
        data = b""
        while len(data) < length:
            part = sock.recv(length - len(data))
            if not part:
                raise RuntimeError("VICTRON_CONNECTION_CLOSED")
            data += part
        return data

    def read_registers(self, unit_id: int, address: int, count: int) -> list[int]:
        self._transaction_id = (self._transaction_id + 1) & 0xFFFF or 1
        pdu = struct.pack(">BHH", 0x03, int(address), int(count))
        frame = struct.pack(">HHHB", self._transaction_id, 0, len(pdu)+1, int(unit_id)) + pdu
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.sendall(frame)
            header = self._recv(sock, 7)
            tid, protocol, length, unit = struct.unpack(">HHHB", header)
            if tid != self._transaction_id or protocol != 0 or unit != int(unit_id):
                raise RuntimeError("VICTRON_MBAP")
            payload = self._recv(sock, length - 1)
        if not payload:
            raise RuntimeError("VICTRON_EMPTY_RESPONSE")
        if payload[0] & 0x80:
            code = payload[1] if len(payload) > 1 else -1
            raise RuntimeError(f"VICTRON_MODBUS_EXCEPTION:{code}")
        if payload[0] != 0x03 or payload[1] != count * 2:
            raise RuntimeError("VICTRON_MODBUS_LENGTH")
        return list(struct.unpack(">" + "H"*count, payload[2:]))

    @staticmethod
    def signed16(value: int) -> int:
        return struct.unpack(">h", struct.pack(">H", value))[0]
