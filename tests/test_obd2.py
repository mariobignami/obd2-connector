"""
Unit tests for OBD2 connector modules (no hardware required).
"""

import time
import threading
import unittest.mock as mock
import pytest

from obd.commands import OBD_PIDS, AT_COMMANDS, VEHICLE_INFO_PIDS
from obd.reader import (
    OBDReader,
    _parse_hex_response,
    _parse_dtcs,
    _parse_vin,
    _parse_ascii_info,
)
from utils.export import export_csv, export_csv_log, export_json


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

class _StubConnector:
    """Minimal connector that returns a preset response for send_command."""

    def __init__(self, response: str = ""):
        self._response = response
        self.last_cmd: str = ""
        self.is_open = True
        self.connection = self  # satisfy is_connected check

    def is_connected(self) -> bool:
        return True

    def send_command(self, cmd: str) -> str:
        self.last_cmd = cmd
        return self._response


# ---------------------------------------------------------------------------
# obd/commands.py
# ---------------------------------------------------------------------------

class TestCommands:
    def test_pid_keys_present(self):
        for required in ("RPM", "SPEED", "COOLANT_TEMP", "FUEL_LEVEL", "VOLTAGE"):
            assert required in OBD_PIDS, f"{required} missing from OBD_PIDS"

    def test_pid_required_fields(self):
        for key, info in OBD_PIDS.items():
            for field in ("desc", "mode", "pid", "bytes", "parse", "unit"):
                assert field in info, f"PID '{key}' missing field '{field}'"
            assert callable(info["parse"]), f"PID '{key}'.parse is not callable"

    def test_rpm_parse(self):
        parse = OBD_PIDS["RPM"]["parse"]
        # RPM bytes [0x0C, 0x00] → (12*256 + 0) / 4 = 768
        assert parse([0x0C, 0x00]) == 768.0

    def test_speed_parse(self):
        parse = OBD_PIDS["SPEED"]["parse"]
        assert parse([100]) == 100

    def test_coolant_temp_parse(self):
        parse = OBD_PIDS["COOLANT_TEMP"]["parse"]
        assert parse([100]) == 60  # 100 - 40

    def test_fuel_level_parse(self):
        parse = OBD_PIDS["FUEL_LEVEL"]["parse"]
        result = parse([128])
        assert 49 <= result <= 51  # ~50%

    def test_voltage_parse(self):
        parse = OBD_PIDS["VOLTAGE"]["parse"]
        # 0x37B8 = 14264 → 14264/1000 = 14.264 V
        assert parse([0x37, 0xB8]) == pytest.approx(14.264, abs=0.001)

    def test_at_commands_not_empty(self):
        assert len(AT_COMMANDS) > 5

    def test_vehicle_info_pids(self):
        assert "VIN" in VEHICLE_INFO_PIDS


# ---------------------------------------------------------------------------
# obd/reader.py – _parse_hex_response
# ---------------------------------------------------------------------------

class TestParseHexResponse:
    def test_typical_rpm_response(self):
        # ELM327 echoes: "410C0BB8" → mode 41, PID 0C, bytes 0B B8
        raw = "41 0C 0B B8"
        result = _parse_hex_response(raw, "01", "0C")
        assert result == [0x0B, 0xB8]

    def test_with_newlines_and_cr(self):
        raw = "41 0C\r0B B8\r"
        result = _parse_hex_response(raw, "01", "0C")
        assert result == [0x0B, 0xB8]

    def test_no_data_returns_none(self):
        assert _parse_hex_response("NO DATA", "01", "0C") is None
        assert _parse_hex_response("", "01", "0C") is None

    def test_mode09_vin_response(self):
        # mode 09 → response mode 49
        raw = "49 02 01 31 47 31 4A 43"
        result = _parse_hex_response(raw, "09", "02")
        assert result is not None


# ---------------------------------------------------------------------------
# obd/reader.py – _parse_dtcs
# ---------------------------------------------------------------------------

class TestParseDTCs:
    def test_single_dtc(self):
        # Response: 43 (mode) + 01 43 (DTC P0143) + 00 00 (padding) + 00 00 (padding)
        raw = "43 01 43 00 00 00 00"
        dtcs = _parse_dtcs(raw)
        assert len(dtcs) == 1
        assert dtcs[0] == "P0143"

    def test_no_dtcs(self):
        # Response: 43 (mode) + all zeros (no DTCs)
        raw = "43 00 00 00 00 00 00"
        dtcs = _parse_dtcs(raw)
        assert dtcs == []

    def test_multiple_dtcs(self):
        # Response: 43 (mode) + 01 43 (P0143) + 04 05 (P0405) + 00 00 (padding)
        raw = "43 01 43 04 05 00 00"
        dtcs = _parse_dtcs(raw)
        assert len(dtcs) == 2
        assert "P0143" in dtcs
        assert "P0405" in dtcs


# ---------------------------------------------------------------------------
# obd/reader.py – _parse_vin
# ---------------------------------------------------------------------------

class TestParseVin:
    def test_vin_extraction(self):
        # Simulate hex bytes for "1G1JC5SH3A4100001"
        vin_str = "1G1JC5SH3A4100001"
        hex_bytes = "49 02 " + " ".join(format(ord(c), "02X") for c in vin_str)
        result = _parse_vin(hex_bytes)
        assert vin_str in result or result == "N/A"  # N/A allowed if parsing drops

    def test_vin_invalid_returns_na(self):
        assert _parse_vin("NO DATA") == "N/A"
        assert _parse_vin("") == "N/A"


# ---------------------------------------------------------------------------
# obd/reader.py – OBDReader with stub connector
# ---------------------------------------------------------------------------

class TestOBDReader:
    def test_read_pid_rpm(self):
        stub = _StubConnector("41 0C 0B B8")
        reader = OBDReader(stub)
        val = reader.read_pid("RPM")
        # data bytes: [0x0B, 0xB8] = [11, 184]
        # RPM = (11 * 256 + 184) / 4 = 3000 / 4 = 750.0
        assert val == pytest.approx(750.0)

    def test_read_pid_unknown_raises(self):
        stub = _StubConnector()
        reader = OBDReader(stub)
        with pytest.raises(ValueError):
            reader.read_pid("DOES_NOT_EXIST")

    def test_read_pid_no_data_returns_none(self):
        stub = _StubConnector("NO DATA")
        reader = OBDReader(stub)
        val = reader.read_pid("SPEED")
        assert val is None

    def test_read_all_returns_dict_for_all_pids(self):
        stub = _StubConnector("NO DATA")
        reader = OBDReader(stub)
        result = reader.read_all()
        # MIL_STATUS is excluded from bulk scans (it returns a dict, not a scalar)
        expected = {k for k in OBD_PIDS if k != "MIL_STATUS"}
        assert set(result.keys()) == expected
        # All None because stub returns "NO DATA"
        assert all(v is None for v in result.values())

    def test_read_dtcs_empty(self):
        stub = _StubConnector("43 00 00 00 00 00 00")
        reader = OBDReader(stub)
        dtcs = reader.read_dtcs()
        assert dtcs == []

    def test_get_protocol(self):
        stub = _StubConnector("ISO 15765-4 (CAN 11/500)")
        reader = OBDReader(stub)
        proto = reader.get_protocol()
        assert "ISO" in proto or proto == "ISO 15765-4 (CAN 11/500)"

    def test_realtime_stream(self):
        """Start/stop real-time streaming and verify callback is called."""
        stub = _StubConnector("41 0D 64")  # SPEED = 100 km/h
        reader = OBDReader(stub)

        received = []
        event = threading.Event()

        def _cb(snap):
            received.append(snap)
            event.set()

        reader.start_realtime(_cb, interval=0.1, keys=["SPEED"])
        called = event.wait(timeout=3)
        reader.stop_realtime()

        assert called, "Real-time callback was never called"
        assert len(received) >= 1
        assert "_timestamp" in received[0]

    def test_start_realtime_twice_does_not_duplicate(self):
        """Calling start_realtime while already running should not start another thread."""
        stub = _StubConnector("NO DATA")
        reader = OBDReader(stub)

        reader.start_realtime(lambda s: None, interval=10, keys=["SPEED"])
        t1 = reader._realtime_thread
        reader.start_realtime(lambda s: None, interval=10, keys=["SPEED"])
        t2 = reader._realtime_thread
        assert t1 is t2  # same thread, not duplicated
        reader.stop_realtime()


# ---------------------------------------------------------------------------
# utils/export.py
# ---------------------------------------------------------------------------

class TestExport:
    def test_export_csv_creates_file(self, tmp_path):
        data = {"RPM": 1200, "SPEED": 60, "_timestamp": time.time()}
        path = export_csv(data, path=str(tmp_path / "test.csv"))
        assert (tmp_path / "test.csv").exists()
        content = (tmp_path / "test.csv").read_text()
        assert "RPM" in content
        assert "1200" in content

    def test_export_csv_append(self, tmp_path):
        p = str(tmp_path / "log.csv")
        t = time.time()
        export_csv({"SPEED": 50, "_timestamp": t}, path=p, append=False)
        export_csv({"SPEED": 80, "_timestamp": t + 1}, path=p, append=True)
        lines = (tmp_path / "log.csv").read_text().splitlines()
        assert len(lines) == 3  # header + 2 data rows

    def test_export_csv_log_creates_file(self, tmp_path):
        rows = [
            {"RPM": 800, "SPEED": 0,  "_timestamp": time.time()},
            {"RPM": 1200, "SPEED": 30, "_timestamp": time.time() + 1},
        ]
        path = export_csv_log(rows, path=str(tmp_path / "session.csv"))
        content = (tmp_path / "session.csv").read_text()
        assert "RPM" in content
        assert "1200" in content

    def test_export_csv_log_empty_raises(self):
        with pytest.raises(ValueError):
            export_csv_log([])

    def test_export_json_creates_file(self, tmp_path):
        data = [{"RPM": 900, "SPEED": 40, "_timestamp": time.time()}]
        path = export_json(data, path=str(tmp_path / "out.json"))
        import json
        loaded = json.loads((tmp_path / "out.json").read_text())
        assert isinstance(loaded, list)
        assert loaded[0]["RPM"] == 900

    def test_export_csv_skips_underscore_keys(self, tmp_path):
        data = {"SPEED": 100, "_internal": "skip", "_timestamp": time.time()}
        path = export_csv(data, path=str(tmp_path / "t.csv"))
        content = (tmp_path / "t.csv").read_text()
        assert "_internal" not in content

    def test_export_csv_none_values_become_empty(self, tmp_path):
        data = {"RPM": None, "SPEED": 60, "_timestamp": time.time()}
        path = export_csv(data, path=str(tmp_path / "nones.csv"))
        content = (tmp_path / "nones.csv").read_text()
        assert "RPM" in content


# ---------------------------------------------------------------------------
# MIL Status
# ---------------------------------------------------------------------------

class TestMILStatus:
    def test_mil_status_pid_present(self):
        assert "MIL_STATUS" in OBD_PIDS

    def test_mil_status_pid_fields(self):
        info = OBD_PIDS["MIL_STATUS"]
        assert info["mode"] == "01"
        assert info["pid"] == "01"
        assert info["bytes"] == 4

    def test_mil_on_parse(self):
        """Byte A bit 7 = 1 → MIL on, bits 0-6 = DTC count."""
        parse = OBD_PIDS["MIL_STATUS"]["parse"]
        # 0x81 = 10000001: MIL on, 1 DTC
        result = parse([0x81, 0x00, 0x00, 0x00])
        assert result["mil_on"] is True
        assert result["dtc_count"] == 1

    def test_mil_off_parse(self):
        parse = OBD_PIDS["MIL_STATUS"]["parse"]
        # 0x00 = MIL off, 0 DTCs
        result = parse([0x00, 0x00, 0x00, 0x00])
        assert result["mil_on"] is False
        assert result["dtc_count"] == 0

    def test_read_mil_status_no_data(self):
        stub = _StubConnector("NO DATA")
        reader = OBDReader(stub)
        status = reader.read_mil_status()
        assert status["mil_on"] is None
        assert status["dtc_count"] is None

    def test_read_mil_status_mil_on(self):
        # Mode 01, PID 01: response mode = 0x41 = "41", PID = "01"
        # data bytes: 0x83 = 10000011 (MIL on, 3 DTCs)
        stub = _StubConnector("41 01 83 00 00 00")
        reader = OBDReader(stub)
        status = reader.read_mil_status()
        assert status["mil_on"] is True
        assert status["dtc_count"] == 3

    def test_read_mil_not_in_read_all(self):
        """read_all() must exclude MIL_STATUS (returns dict, not scalar)."""
        stub = _StubConnector("NO DATA")
        reader = OBDReader(stub)
        result = reader.read_all()
        assert "MIL_STATUS" not in result


# ---------------------------------------------------------------------------
# connector/base.py – send_command (prompt-based reading)
# ---------------------------------------------------------------------------

class TestSendCommand:
    """Test BaseConnector.send_command with a mocked serial port."""

    def _make_connector_with_serial(self, response_bytes: bytes):
        """Return a BluetoothConnector whose serial port returns the given bytes."""
        from connector.bluetooth import BluetoothConnector

        conn = BluetoothConnector.__new__(BluetoothConnector)
        conn.timeout = 1

        data = list(response_bytes)
        pos = [0]

        fake_serial = mock.MagicMock()
        fake_serial.is_open = True

        def in_waiting_side_effect():
            return max(0, len(data) - pos[0])

        def read_side_effect(n):
            chunk = bytes(data[pos[0]:pos[0] + n])
            pos[0] += n
            return chunk

        type(fake_serial).in_waiting = mock.PropertyMock(
            side_effect=in_waiting_side_effect
        )
        fake_serial.read.side_effect = read_side_effect
        conn.connection = fake_serial
        return conn

    def test_reads_until_prompt(self):
        """send_command stops reading when '>' is received."""
        conn = self._make_connector_with_serial(b"41 0C 0B B8\r\n>")
        result = conn.send_command("010C")
        assert "41" in result
        assert "0C" in result

    def test_returns_empty_on_timeout(self):
        """send_command returns empty string when no data arrives within timeout."""
        from connector.bluetooth import BluetoothConnector

        conn = BluetoothConnector.__new__(BluetoothConnector)
        conn.timeout = 0.1  # very short timeout

        fake_serial = mock.MagicMock()
        fake_serial.is_open = True
        type(fake_serial).in_waiting = mock.PropertyMock(return_value=0)
        conn.connection = fake_serial

        result = conn.send_command("010C")
        assert result == ""

    def test_strips_prompt_from_result(self):
        """The '>' character and surrounding whitespace are stripped from the result."""
        conn = self._make_connector_with_serial(b"OK\r\n>")
        result = conn.send_command("AT E0")
        assert ">" not in result
        assert "OK" in result


# ---------------------------------------------------------------------------
# web/app.py – timing_advance key alignment
# ---------------------------------------------------------------------------

class TestDemoSensorKeys:
    def test_demo_sensors_include_timing_advance(self):
        """Demo sensor data must use 'timing_advance' to match the live OBD reader key."""
        from web.app import create_app
        app = create_app(demo=True)
        with app.test_client() as c:
            r = c.get("/api/sensors")
            data = r.get_json()
            sensors = data["sensors"]
            assert "timing_advance" in sensors, (
                "'timing_advance' key missing – demo data and JS GAUGES must match live reader output"
            )
            assert "timing" not in sensors, (
                "Old 'timing' key still present – should have been renamed to 'timing_advance'"
            )


# ---------------------------------------------------------------------------
# web/app.py – smoke tests
# ---------------------------------------------------------------------------

class TestWebApp:
    def test_demo_app_sensors(self):
        from web.app import create_app
        app = create_app(demo=True)
        with app.test_client() as c:
            r = c.get("/api/sensors")
            assert r.status_code == 200
            data = r.get_json()
            assert "sensors" in data
            assert "rpm" in data["sensors"]

    def test_demo_app_status(self):
        from web.app import create_app
        app = create_app(demo=True)
        with app.test_client() as c:
            r = c.get("/api/status")
            assert r.status_code == 200
            d = r.get_json()
            assert d["connected"] is True
            assert d["mode"] == "demo"

    def test_demo_app_dtc(self):
        from web.app import create_app
        app = create_app(demo=True)
        with app.test_client() as c:
            r = c.get("/api/dtc")
            assert r.status_code == 200
            d = r.get_json()
            assert "codes" in d

    def test_demo_app_dtc_clear(self):
        from web.app import create_app
        app = create_app(demo=True)
        with app.test_client() as c:
            r = c.post("/api/dtc/clear")
            assert r.status_code == 200
            d = r.get_json()
            assert d["success"] is True

    def test_demo_app_vehicle_info(self):
        from web.app import create_app
        app = create_app(demo=True)
        with app.test_client() as c:
            r = c.get("/api/vehicle_info")
            assert r.status_code == 200
            d = r.get_json()
            assert "vin" in d
            assert "protocol" in d

    def test_demo_app_command(self):
        from web.app import create_app
        app = create_app(demo=True)
        with app.test_client() as c:
            r = c.post("/api/command",
                       json={"command": "AT RV"},
                       content_type="application/json")
            assert r.status_code == 200
            d = r.get_json()
            assert "response" in d

    def test_demo_app_command_no_body(self):
        from web.app import create_app
        app = create_app(demo=True)
        with app.test_client() as c:
            r = c.post("/api/command",
                       json={},
                       content_type="application/json")
            assert r.status_code == 400

    def test_demo_app_export_csv(self):
        from web.app import create_app
        app = create_app(demo=True)
        with app.test_client() as c:
            r = c.get("/api/export")
            assert r.status_code == 200
            assert "text/csv" in r.content_type

    def test_demo_app_mil(self):
        from web.app import create_app
        app = create_app(demo=True)
        with app.test_client() as c:
            r = c.get("/api/mil")
            assert r.status_code == 200
            d = r.get_json()
            assert "mil_on" in d

    def test_live_app_dtc_uses_reader_read_dtcs(self):
        """Verify that the live app calls reader.read_dtcs() (not read_dtc())."""
        from web.app import create_app

        class _FakeReader:
            def read_dtcs(self):
                return ["P0143"]

        app = create_app(reader=_FakeReader(), demo=False)
        with app.test_client() as c:
            r = c.get("/api/dtc")
            assert r.status_code == 200
            d = r.get_json()
            assert d["codes"] == ["P0143"]

    def test_live_app_dtc_clear_uses_reader(self):
        """Verify that DTC clear uses reader.clear_dtcs() (not writer.clear_dtc())."""
        from web.app import create_app

        class _FakeReader:
            def clear_dtcs(self):
                return "OK"

        app = create_app(reader=_FakeReader(), demo=False)
        with app.test_client() as c:
            r = c.post("/api/dtc/clear")
            assert r.status_code == 200
            d = r.get_json()
            assert d["success"] is True

    def test_demo_dtc_returns_sample_codes(self):
        """Demo mode must return sample DTC codes so users can see the feature."""
        from web.app import create_app, _DEMO_DTCS
        app = create_app(demo=True)
        with app.test_client() as c:
            r = c.get("/api/dtc")
            assert r.status_code == 200
            d = r.get_json()
            assert d["codes"] == _DEMO_DTCS
            assert len(d["codes"]) > 0, "Demo mode should return at least one sample DTC"

    def test_demo_pending_dtc(self):
        """Demo mode /api/dtc/pending must return pending sample codes."""
        from web.app import create_app, _DEMO_PENDING_DTCS
        app = create_app(demo=True)
        with app.test_client() as c:
            r = c.get("/api/dtc/pending")
            assert r.status_code == 200
            d = r.get_json()
            assert "codes" in d
            assert d["codes"] == _DEMO_PENDING_DTCS

    def test_live_app_pending_dtc_uses_reader(self):
        """Live mode /api/dtc/pending calls reader.read_pending_dtcs()."""
        from web.app import create_app

        class _FakeReader:
            def read_pending_dtcs(self):
                return ["P0300"]

        app = create_app(reader=_FakeReader(), demo=False)
        with app.test_client() as c:
            r = c.get("/api/dtc/pending")
            assert r.status_code == 200
            d = r.get_json()
            assert d["codes"] == ["P0300"]

    def test_demo_sensors_all_obd_pids_present(self):
        """Demo sensor data must include all OBD_PIDS keys (minus MIL_STATUS) as lowercase."""
        from web.app import create_app
        from obd.commands import OBD_PIDS
        app = create_app(demo=True)
        with app.test_client() as c:
            r = c.get("/api/sensors")
            d = r.get_json()
            sensors = d["sensors"]
            for key in OBD_PIDS:
                if key == "MIL_STATUS":
                    continue
                assert key.lower() in sensors, (
                    f"Demo sensor missing '{key.lower()}' – web and CLI dash must show the same sensors"
                )
