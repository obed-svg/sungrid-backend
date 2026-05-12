"""RWK35 DNP3 protocol frame builder/parser.

Ported from examples/RWK35/read_rwk35.py to match the current device firmware.
"""

from __future__ import annotations

import asyncio
import socket
import struct
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


def crc16_dnp(data: bytes) -> int:
    poly = 0x3D65
    crc = 0x0000
    for byte in data:
        reflected_byte = 0
        for i in range(8):
            if (byte >> i) & 1:
                reflected_byte |= 1 << (7 - i)
        crc ^= (reflected_byte << 8)
        for _ in range(8):
            crc = (crc << 1) ^ poly if (crc & 0x8000) else (crc << 1)
    crc &= 0xFFFF
    reflected_crc = 0
    for i in range(16):
        if (crc >> i) & 1:
            reflected_crc |= 1 << (15 - i)
    return reflected_crc ^ 0xFFFF


def build_frame(src: int, dst: int, app_payload: bytes) -> bytes:
    length = 5 + len(app_payload)
    header = bytes(
        [
            0x05,
            0x64,
            length,
            0xC4,
            dst & 0xFF,
            (dst >> 8) & 0xFF,
            src & 0xFF,
            (src >> 8) & 0xFF,
        ]
    )
    frame = header + struct.pack("<H", crc16_dnp(header))
    offset = 0
    while offset < len(app_payload):
        block = app_payload[offset : offset + 16]
        frame += block + struct.pack("<H", crc16_dnp(block))
        offset += 16
    return frame


def build_read_class0(src: int, dst: int, seq: int) -> bytes:
    ctrl = 0xC0 | (seq & 0x0F)
    app = bytes([ctrl, ctrl, 0x01, 0x3C, 0x01, 0x06])
    return build_frame(src, dst, app)


# Control frames from examples/RWK35/trip_and_close.py
CLOSE_FRAME = bytes.fromhex(
    "05641AC4010002004F53DCCC050C01280100F4018101000000005B91F4010000000E52"
)
TRIP_FRAME = bytes.fromhex(
    "05641AC4010002004F53DDCD050C01280100F601810100000000EB9EF4010000000E52"
)


def strip_crc_blocks(raw: bytes) -> bytes:
    result = b""
    offset = 0
    while offset < len(raw):
        end = min(offset + 16, len(raw))
        result += raw[offset:end]
        offset = end + 2
    return result


def recv_dnp3_frame(sock: socket.socket) -> bytes:
    header = b""
    while len(header) < 2:
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("Socket closed")
        if not header and chunk == b"\x05":
            header = b"\x05"
        elif header == b"\x05" and chunk == b"\x64":
            header = b"\x05\x64"
        else:
            header = b""
    while len(header) < 10:
        chunk = sock.recv(10 - len(header))
        if not chunk:
            raise ConnectionError("Socket closed")
        header += chunk
    length = header[2]
    app_size = length - 5
    num_blocks = (app_size + 15) // 16
    payload_size = app_size + num_blocks * 2
    payload = b""
    while len(payload) < payload_size:
        chunk = sock.recv(payload_size - len(payload))
        if not chunk:
            raise ConnectionError("Socket closed")
        payload += chunk
    return header + payload


async def recv_dnp3_frame_async(reader: asyncio.StreamReader) -> bytes:
    """Async version of recv_dnp3_frame."""
    header = b""
    while len(header) < 2:
        chunk = await reader.read(1)
        if not chunk:
            raise ConnectionError("Socket closed")
        if not header and chunk == b"\x05":
            header = b"\x05"
        elif header == b"\x05" and chunk == b"\x64":
            header = b"\x05\x64"
        else:
            header = b""
    while len(header) < 10:
        chunk = await reader.read(10 - len(header))
        if not chunk:
            raise ConnectionError("Socket closed")
        header += chunk
    length = header[2]
    app_size = length - 5
    num_blocks = (app_size + 15) // 16
    payload_size = app_size + num_blocks * 2
    payload = b""
    while len(payload) < payload_size:
        chunk = await reader.read(payload_size - len(payload))
        if not chunk:
            raise ConnectionError("Socket closed")
        payload += chunk
    return header + payload


def validate_header_crc(data: bytes) -> bool:
    return len(data) >= 10 and crc16_dnp(data[:8]) == struct.unpack("<H", data[8:10])[0]


_update_counts: dict[int, int] = {}
_last_values: dict[int, object] = {}
_change_counts: dict[int, int] = {}

BI_LABELS: dict[int, str] = {
    1: "Remote Enabled",
    2: "Start action",
    3: "Action",
    4: "Freq.Low Enable(Grp)",
    5: "Freq.High Enable(Grp)",
    6: "Freq.Slip Enable(Grp)",
    7: "L.Over volt1 Enable(Grp)",
    8: "L.Over volt2 Enable(Grp)",
    9: "L.Under volt1 En.(Grp)",
    10: "L.Under volt2 En.(Grp)",
    11: "Breaker close",
    12: "Breaker open",
    13: "Protection Enabled",
    14: "Ground Enabled",
    15: "Group1",
    16: "Group2",
    17: "Line over-voltage1",
    18: "Line over-voltage2",
    19: "Line under-voltage1",
    20: "Line under-voltage2",
    21: "Zero-seq over-volt",
    22: "Phase OC1 trip",
    23: "Phase fast curve",
    24: "Ground OC1 trip",
    25: "Ground fast curve",
    26: "Low frequency",
    27: "High frequency",
    28: "Frequency slip",
}

AI_LABELS: dict[int, str] = {
    2000: "Ia",
    2001: "Ib",
    2002: "Ic",
    2003: "3I0",
    2004: "Ua",
    2005: "Ub",
    2006: "Uc",
    2007: "Ur",
    2008: "Us",
    2009: "Ut",
    2010: "F_ABC",
    2011: "F_RST",
    2012: "AP",
    2013: "P",
    2014: "PF",
    2015: "Q",
}


def parse_response(data: bytes, rx_time: datetime) -> list[dict]:
    if not validate_header_crc(data):
        return []

    app = strip_crc_blocks(data[10:])

    if len(app) < 5:
        return []

    func = app[2]
    if func not in (0x81, 0x82):
        return []

    points: list[dict] = []
    i = 5

    while i + 3 <= len(app):
        group = app[i]
        var = app[i + 1]
        qualifier = app[i + 2]
        i += 3

        if qualifier == 0x01:
            if i + 4 > len(app):
                break
            start = struct.unpack("<H", app[i : i + 2])[0]
            stop = struct.unpack("<H", app[i + 2 : i + 4])[0]
            i += 4
            count = stop - start + 1

            if group == 1 and var == 2:
                for j in range(count):
                    if i >= len(app):
                        break
                    flag = app[i]
                    i += 1
                    idx = start + j
                    value = bool(flag & 0x80)
                    _update_counts[idx] = _update_counts.get(idx, 0) + 1
                    _change_counts[idx] = _change_counts.get(idx, 0)
                    if idx in _last_values and _last_values[idx] != value:
                        _change_counts[idx] += 1
                    _last_values[idx] = value
                    points.append(
                        {
                            "name": BI_LABELS.get(idx, f"Binary_{idx}"),
                            "value": value,
                            "timestamp": rx_time,
                            "quality_online": bool(flag & 0x01),
                            "id": idx,
                            "count_update": _update_counts[idx],
                            "change_count": _change_counts[idx],
                            "type": "binary",
                        }
                    )

            elif group == 30 and var == 5:
                for j in range(count):
                    if i + 5 > len(app):
                        break
                    flag = app[i]
                    value = struct.unpack("<f", app[i + 1 : i + 5])[0]
                    i += 5
                    idx = start + j
                    _update_counts[idx] = _update_counts.get(idx, 0) + 1
                    _change_counts[idx] = _change_counts.get(idx, 0)
                    if idx in _last_values and _last_values[idx] != value:
                        _change_counts[idx] += 1
                    _last_values[idx] = value
                    points.append(
                        {
                            "name": AI_LABELS.get(idx, f"Analog_{idx}"),
                            "value": value,
                            "timestamp": rx_time,
                            "quality_online": bool(flag & 0x01),
                            "id": idx,
                            "count_update": _update_counts[idx],
                            "change_count": _change_counts[idx],
                            "type": "analog",
                        }
                    )

            elif group == 30 and var == 2:
                for j in range(count):
                    if i + 3 > len(app):
                        break
                    flag = app[i]
                    value = struct.unpack("<h", app[i + 1 : i + 3])[0]
                    i += 3
                    idx = start + j
                    _update_counts[idx] = _update_counts.get(idx, 0) + 1
                    _change_counts[idx] = _change_counts.get(idx, 0)
                    if idx in _last_values and _last_values[idx] != value:
                        _change_counts[idx] += 1
                    _last_values[idx] = value
                    points.append(
                        {
                            "name": AI_LABELS.get(idx, f"Analog_{idx}"),
                            "value": float(value),
                            "timestamp": rx_time,
                            "quality_online": bool(flag & 0x01),
                            "id": idx,
                            "count_update": _update_counts[idx],
                            "change_count": _change_counts[idx],
                            "type": "analog",
                        }
                    )

            else:
                break

        elif qualifier == 0x00:
            if i + 2 > len(app):
                break
            start = app[i]
            stop = app[i + 1]
            i += 2
            count = stop - start + 1

            if group == 1 and var == 2:
                for j in range(count):
                    if i >= len(app):
                        break
                    flag = app[i]
                    i += 1
                    idx = start + j
                    value = bool(flag & 0x80)
                    _update_counts[idx] = _update_counts.get(idx, 0) + 1
                    _change_counts[idx] = _change_counts.get(idx, 0)
                    if idx in _last_values and _last_values[idx] != value:
                        _change_counts[idx] += 1
                    _last_values[idx] = value
                    points.append(
                        {
                            "name": BI_LABELS.get(idx, f"Binary_{idx}"),
                            "value": value,
                            "timestamp": rx_time,
                            "quality_online": bool(flag & 0x01),
                            "id": idx,
                            "count_update": _update_counts[idx],
                            "change_count": _change_counts[idx],
                            "type": "binary",
                        }
                    )

            elif group == 30 and var == 5:
                for j in range(count):
                    if i + 5 > len(app):
                        break
                    flag = app[i]
                    value = struct.unpack("<f", app[i + 1 : i + 5])[0]
                    i += 5
                    idx = start + j
                    _update_counts[idx] = _update_counts.get(idx, 0) + 1
                    _change_counts[idx] = _change_counts.get(idx, 0)
                    if idx in _last_values and _last_values[idx] != value:
                        _change_counts[idx] += 1
                    _last_values[idx] = value
                    points.append(
                        {
                            "name": AI_LABELS.get(idx, f"Analog_{idx}"),
                            "value": value,
                            "timestamp": rx_time,
                            "quality_online": bool(flag & 0x01),
                            "id": idx,
                            "count_update": _update_counts[idx],
                            "change_count": _change_counts[idx],
                            "type": "analog",
                        }
                    )

            elif group == 30 and var == 2:
                for j in range(count):
                    if i + 3 > len(app):
                        break
                    flag = app[i]
                    value = struct.unpack("<h", app[i + 1 : i + 3])[0]
                    i += 3
                    idx = start + j
                    _update_counts[idx] = _update_counts.get(idx, 0) + 1
                    _change_counts[idx] = _change_counts.get(idx, 0)
                    if idx in _last_values and _last_values[idx] != value:
                        _change_counts[idx] += 1
                    _last_values[idx] = value
                    points.append(
                        {
                            "name": AI_LABELS.get(idx, f"Analog_{idx}"),
                            "value": float(value),
                            "timestamp": rx_time,
                            "quality_online": bool(flag & 0x01),
                            "id": idx,
                            "count_update": _update_counts[idx],
                            "change_count": _change_counts[idx],
                            "type": "analog",
                        }
                    )
            else:
                break

        elif qualifier == 0x28:
            if i + 2 > len(app):
                break
            count = struct.unpack("<H", app[i : i + 2])[0]
            i += 2

            if group == 2 and var == 2:
                for _ in range(count):
                    if i + 9 > len(app):
                        break
                    idx = struct.unpack("<H", app[i : i + 2])[0]
                    flag = app[i + 2]
                    i += 9
                    value = bool(flag & 0x80)
                    _update_counts[idx] = _update_counts.get(idx, 0) + 1
                    _change_counts[idx] = _change_counts.get(idx, 0)
                    if idx in _last_values and _last_values[idx] != value:
                        _change_counts[idx] += 1
                    _last_values[idx] = value
                    points.append(
                        {
                            "name": BI_LABELS.get(idx, f"Binary_{idx}"),
                            "value": value,
                            "timestamp": rx_time,
                            "quality_online": bool(flag & 0x01),
                            "id": idx,
                            "count_update": _update_counts[idx],
                            "change_count": _change_counts[idx],
                            "type": "binary",
                        }
                    )
            else:
                break

        else:
            break

    return points


def flush_socket(sock: socket.socket, timeout: float = 1.5) -> int:
    """Read and discard any buffered data until socket is quiet."""
    sock.settimeout(timeout)
    total = 0
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            total += len(chunk)
            deadline = time.monotonic() + 0.3
        except (TimeoutError, asyncio.TimeoutError):
            break
    return total


async def flush_socket_async(reader: asyncio.StreamReader, timeout: float = 1.5) -> int:
    """Async version of flush_socket."""
    total = 0
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        try:
            chunk = await asyncio.wait_for(reader.read(4096), timeout=0.3)
            if not chunk:
                break
            total += len(chunk)
            deadline = asyncio.get_event_loop().time() + 0.3
        except (TimeoutError, asyncio.TimeoutError, asyncio.CancelledError):
            break
    return total


def recv_solicited(sock: socket.socket, timeout: float = 10) -> bytes | None:
    """Read frames until we get a solicited response (func=0x81) with FIN=1."""
    sock.settimeout(timeout)
    deadline = time.monotonic() + timeout
    all_resp = b""
    while time.monotonic() < deadline:
        try:
            resp = recv_dnp3_frame(sock)
        except (TimeoutError, socket.timeout):  # noqa: UP041
            return None
        app = strip_crc_blocks(resp[10:])
        if len(app) >= 3 and app[2] == 0x81:
            all_resp = resp
            if app[1] & 0x40:
                return all_resp
    return all_resp or None


async def recv_solicited_async(reader: asyncio.StreamReader, timeout: float = 10) -> bytes | None:
    """Async version of recv_solicited."""
    deadline = asyncio.get_event_loop().time() + timeout
    all_resp = b""
    while asyncio.get_event_loop().time() < deadline:
        try:
            resp = await asyncio.wait_for(recv_dnp3_frame_async(reader), timeout=timeout)
        except (TimeoutError, asyncio.TimeoutError):  # noqa: UP041
            return None
        app = strip_crc_blocks(resp[10:])
        if len(app) >= 3 and app[2] == 0x81:
            all_resp = resp
            if app[1] & 0x40:
                return all_resp
    return all_resp or None


# Hot field mapping for TelemetryRecord
AI_HOT_MAP: dict[str, str | None] = {
    "Ia": "ia",
    "Ib": "ib",
    "Ic": "ic",
    "3I0": "i_neutral",
    "Ua": "ua",
    "Ub": "ub",
    "Uc": "uc",
    "Ur": "ur",
    "Us": "us",
    "Ut": "ut",
    "F_ABC": "freq",
    "F_RST": None,
    "AP": None,
    "P": "p",
    "PF": "pf",
    "Q": "q",
}

BI_HOT_MAP: dict[str, str | None] = {
    "Breaker close": "breaker_close",
    "Breaker open": "breaker_open",
}


def extract_hot_fields(points: list[dict]) -> dict[str, float | bool | None]:
    """Extract hot fields from parsed points for TelemetryRecord."""
    hot: dict[str, float | bool | None] = {}
    for p in points:
        if not p.get("quality_online"):
            continue
        if p.get("type") == "analog":
            field = AI_HOT_MAP.get(p["name"])
            if field:
                hot[field] = p["value"]
        elif p.get("type") == "binary":
            field = BI_HOT_MAP.get(p["name"])
            if field:
                hot[field] = p["value"]
    return hot


def voltages_match(hot: dict, tol: float = 0.05) -> bool:
    """Check if input and output voltages match within tolerance."""
    pairs = [("ua", "ur"), ("ub", "us"), ("uc", "ut")]
    for i_key, o_key in pairs:
        vi = hot.get(i_key)
        vo = hot.get(o_key)
        if vi is None or vo is None or vi <= 0.1:
            continue
        if abs(vi - vo) > tol * abs(vi):
            return False
    return True


def compute_derived_status(hot: dict) -> str:
    """Compute derived status using ONLY voltage comparison.

    CLOSED: input voltages match output voltages, OR outputs are present and > 1.0 kV
    OPEN:  outputs are near zero (< 1.0 kV) with at least one input present
    ERROR: only when all voltages are 0 or missing
    """
    ua = hot.get("ua") or 0
    ub = hot.get("ub") or 0
    uc = hot.get("uc") or 0
    ur = hot.get("ur") or 0
    us = hot.get("us") or 0
    ut = hot.get("ut") or 0

    # ERROR only when all voltages are 0 or missing
    all_zero = (
        ua <= 0.1 and ub <= 0.1 and uc <= 0.1
        and ur <= 0.1 and us <= 0.1 and ut <= 0.1
    )
    if all_zero:
        return "ERROR"

    # Check if outputs are present and above 1.0 kV -> CLOSED
    outputs_present = ur > 1.0 and us > 1.0 and ut > 1.0
    if outputs_present:
        return "CLOSED"

    # Check if outputs are near zero -> OPEN
    outputs_near_zero = ur < 1.0 and us < 1.0 and ut < 1.0
    if outputs_near_zero:
        return "OPEN"

    # Check if input/output voltages match -> CLOSED
    if voltages_match(hot):
        return "CLOSED"

    return "ERROR"
