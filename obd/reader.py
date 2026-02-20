"""
OBD2 reader – single PID, bulk scan, and real-time streaming.
"""

import time
import threading
from typing import Any, Callable, Dict, Optional

from .commands import OBD_PIDS, VEHICLE_INFO_PIDS


# ---------------------------------------------------------------------------
# Raw response helpers
# ---------------------------------------------------------------------------

def _parse_hex_response(raw: str, mode: str, pid: str) -> Optional[list]:
    """
    Extract the data bytes from an ELM327 response string.

    Returns a list of integer byte values, or None on error.
    """
    raw = raw.strip().upper().replace("\r", " ").replace("\n", " ")
    # Remove echo (command may be echoed back)
    expected_header = (mode + pid).upper()
    lines = raw.split()

    # Collect only hex tokens
    hex_tokens = [t for t in lines if all(c in "0123456789ABCDEF" for c in t) and len(t) == 2]

    if not hex_tokens:
        return None

    # The response mode is request mode + 0x40
    response_mode = format(int(mode, 16) + 0x40, "02X")
    try:
        idx = hex_tokens.index(response_mode)
        # Validate that the next token matches the expected PID
        if idx + 1 < len(hex_tokens) and hex_tokens[idx + 1] != pid.upper():
            return None
        # Data bytes start after response_mode + PID
        data = hex_tokens[idx + 2:]
        return [int(b, 16) for b in data] if data else None
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# OBDReader
# ---------------------------------------------------------------------------

class OBDReader:
    """Reads OBD2 sensor data through a BaseConnector."""

    def __init__(self, connector):
        self.connector = connector
        self._stop_event = threading.Event()
        self._realtime_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Single PID read
    # ------------------------------------------------------------------

    def read_pid(self, key: str) -> Optional[Any]:
        """
        Read a single PID by its key (e.g. 'RPM', 'SPEED').

        Returns the parsed numeric value, or None if unavailable/error.
        """
        if key not in OBD_PIDS:
            raise ValueError(f"Unknown PID key: '{key}'. Available: {list(OBD_PIDS)}")

        info = OBD_PIDS[key]
        cmd = info["mode"] + info["pid"]
        try:
            raw = self.connector.send_command(cmd)
            data = _parse_hex_response(raw, info["mode"], info["pid"])
            if data and len(data) >= info["bytes"]:
                return info["parse"](data[:info["bytes"]])
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Bulk scan
    # ------------------------------------------------------------------

    def read_all(self) -> Dict[str, Any]:
        """
        Read all defined PIDs and return a dict of {key: value | None}.
        Values are None when the vehicle does not support that PID.
        """
        results: Dict[str, Any] = {}
        for key in OBD_PIDS:
            results[key] = self.read_pid(key)
        return results

    def read_supported_pids(self) -> Dict[str, Any]:
        """
        Read only the PIDs that return a non-None value (supported by ECU).
        """
        return {k: v for k, v in self.read_all().items() if v is not None}

    # ------------------------------------------------------------------
    # DTC reading
    # ------------------------------------------------------------------

    def read_dtcs(self) -> list:
        """
        Read stored DTCs (Mode 03). Returns a list of DTC strings.
        """
        try:
            raw = self.connector.send_command("03")
            return _parse_dtcs(raw)
        except Exception:
            return []

    def read_pending_dtcs(self) -> list:
        """
        Read pending DTCs (Mode 07). Returns a list of DTC strings.
        """
        try:
            raw = self.connector.send_command("07")
            return _parse_dtcs(raw)
        except Exception:
            return []

    def clear_dtcs(self) -> str:
        """
        Clear all stored DTCs (Mode 04).
        """
        try:
            return self.connector.send_command("04")
        except Exception as exc:
            return f"ERROR: {exc}"

    # ------------------------------------------------------------------
    # Freeze frame  (Mode 02)
    # ------------------------------------------------------------------

    def read_freeze_frame(self, key: str, frame: int = 0) -> Optional[Any]:
        """
        Read a freeze-frame PID (Mode 02).
        frame – freeze frame number (0 = first)
        """
        if key not in OBD_PIDS:
            raise ValueError(f"Unknown PID key: '{key}'")
        info = OBD_PIDS[key]
        cmd = "02" + info["pid"] + format(frame, "02X")
        try:
            raw = self.connector.send_command(cmd)
            data = _parse_hex_response(raw, "02", info["pid"])
            if data and len(data) >= info["bytes"]:
                return info["parse"](data[:info["bytes"]])
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Vehicle info  (Mode 09)
    # ------------------------------------------------------------------

    def read_vin(self) -> str:
        """Read the Vehicle Identification Number (VIN) via Mode 09 PID 02."""
        try:
            self.connector.send_command("AT H1")   # headers on to reassemble
            raw = self.connector.send_command("0902")
            self.connector.send_command("AT H0")   # headers off again
            return _parse_vin(raw)
        except Exception:
            return "N/A"

    def read_ecu_name(self) -> str:
        """Read the ECU name via Mode 09 PID 0A."""
        try:
            raw = self.connector.send_command("090A")
            return _parse_ascii_info(raw)
        except Exception:
            return "N/A"

    def read_calibration_id(self) -> str:
        """Read the calibration ID via Mode 09 PID 04."""
        try:
            raw = self.connector.send_command("0904")
            return _parse_ascii_info(raw)
        except Exception:
            return "N/A"

    # ------------------------------------------------------------------
    # OBD protocol detection
    # ------------------------------------------------------------------

    def get_protocol(self) -> str:
        """Return the currently used OBD protocol description."""
        try:
            return self.connector.send_command("AT DP").strip()
        except Exception:
            return "N/A"

    def get_protocol_number(self) -> str:
        """Return the currently used OBD protocol number."""
        try:
            return self.connector.send_command("AT DPN").strip()
        except Exception:
            return "N/A"

    def get_elm_version(self) -> str:
        """Return the ELM327 chip version string."""
        try:
            return self.connector.send_command("AT I").strip()
        except Exception:
            return "N/A"

    def get_battery_voltage(self) -> str:
        """Return battery voltage reported by the ELM327 (AT RV)."""
        try:
            return self.connector.send_command("AT RV").strip()
        except Exception:
            return "N/A"

    # ------------------------------------------------------------------
    # Real-time streaming
    # ------------------------------------------------------------------

    def start_realtime(
        self,
        callback: Callable[[Dict[str, Any]], None],
        interval: float = 1.0,
        keys: Optional[list] = None,
    ) -> None:
        """
        Start a background thread that calls `callback` with a fresh
        snapshot dict every `interval` seconds.

        callback receives: {"key": value_or_None, …, "_timestamp": float}
        """
        if self._realtime_thread and self._realtime_thread.is_alive():
            return  # already running

        self._stop_event.clear()
        selected_keys = keys if keys else list(OBD_PIDS.keys())

        def _loop():
            while not self._stop_event.is_set():
                snapshot: Dict[str, Any] = {}
                for k in selected_keys:
                    if self._stop_event.is_set():
                        break
                    snapshot[k] = self.read_pid(k)
                snapshot["_timestamp"] = time.time()
                callback(snapshot)
                self._stop_event.wait(interval)

        self._realtime_thread = threading.Thread(target=_loop, daemon=True)
        self._realtime_thread.start()

    def stop_realtime(self) -> None:
        """Stop the background real-time reading thread."""
        self._stop_event.set()
        if self._realtime_thread:
            self._realtime_thread.join(timeout=5)


# ---------------------------------------------------------------------------
# DTC / VIN parsing helpers (module-private)
# ---------------------------------------------------------------------------

_DTC_PREFIX_MAP = {
    0b00: "P0",
    0b01: "P1",
    0b10: "P2",
    0b11: "P3",
    # chassis / body / network: second nibble of first byte
}

_DTC_FIRST_CHAR = {
    0: "P",
    1: "C",
    2: "B",
    3: "U",
}


def _parse_dtcs(raw: str) -> list:
    """Parse a Mode 03 / 07 response into a list of DTC strings."""
    raw = raw.strip().upper().replace("\r", " ").replace("\n", " ")
    tokens = raw.split()
    hex_tokens = [t for t in tokens if all(c in "0123456789ABCDEF" for c in t) and len(t) == 2]

    # Skip the leading response mode byte (43 = Mode 03, 47 = Mode 07)
    if hex_tokens and hex_tokens[0] in ("43", "47"):
        hex_tokens = hex_tokens[1:]

    dtcs = []
    i = 0
    while i + 1 < len(hex_tokens):
        high = int(hex_tokens[i], 16)
        low = int(hex_tokens[i + 1], 16)
        i += 2
        if high == 0 and low == 0:
            continue
        system = (high & 0xC0) >> 6
        prefix = _DTC_FIRST_CHAR.get(system, "P")
        digit2 = (high & 0x30) >> 4
        digit3 = high & 0x0F
        digit4 = (low & 0xF0) >> 4
        digit5 = low & 0x0F
        dtc = f"{prefix}{digit2}{digit3:X}{digit4:X}{digit5:X}"
        dtcs.append(dtc)
    return dtcs


def _parse_vin(raw: str) -> str:
    """Extract ASCII VIN from a raw Mode 09 PID 02 multi-frame response."""
    raw = raw.upper().replace("\r", " ").replace("\n", " ")
    tokens = raw.split()
    hex_tokens = [t for t in tokens if all(c in "0123456789ABCDEF" for c in t) and len(t) == 2]

    # Drop frame headers / mode/pid bytes (49 02 …)
    collecting = False
    chars = []
    for t in hex_tokens:
        if t == "49":
            collecting = True
            continue
        if collecting:
            val = int(t, 16)
            if 0x20 <= val <= 0x7E:
                chars.append(chr(val))
    vin = "".join(chars).strip()
    return vin if len(vin) >= 5 else "N/A"


def _parse_ascii_info(raw: str) -> str:
    """Generic ASCII text parser for Mode 09 string responses."""
    raw = raw.upper().replace("\r", " ").replace("\n", " ")
    tokens = raw.split()
    hex_tokens = [t for t in tokens if all(c in "0123456789ABCDEF" for c in t) and len(t) == 2]
    chars = [chr(int(t, 16)) for t in hex_tokens if 0x20 <= int(t, 16) <= 0x7E]
    return "".join(chars).strip() or "N/A"
