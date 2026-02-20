"""pytest test suite for the OBD2 connector project."""

import csv
import io
import json
import os
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def make_mock_connector(response="41 0C 1A F8\r\n>"):
    """Return a mock connector whose send_command returns *response*."""
    conn = MagicMock()
    conn.send_command.return_value = response
    conn.is_connected.return_value = True
    conn.port = "/dev/ttyTEST"
    return conn


# ---------------------------------------------------------------------------
# 1. connector/base.py — is_open (not isOpen)
# ---------------------------------------------------------------------------

def test_base_connector_is_open():
    """BaseConnector uses is_open, not the deprecated isOpen()."""
    from connector.base import BaseConnector

    class _Concrete(BaseConnector):
        def connect(self):
            return True

    c = _Concrete(port="/dev/null")
    mock_serial = MagicMock()
    mock_serial.is_open = True
    c.connection = mock_serial
    assert c.is_connected() is True


def test_base_connector_disconnect():
    from connector.base import BaseConnector

    class _Concrete(BaseConnector):
        def connect(self):
            return True

    c = _Concrete(port="/dev/null")
    mock_serial = MagicMock()
    mock_serial.is_open = True
    c.connection = mock_serial
    c.disconnect()
    mock_serial.close.assert_called_once()


def test_base_connector_send_command():
    from connector.base import BaseConnector

    class _Concrete(BaseConnector):
        def connect(self):
            return True

    c = _Concrete(port="/dev/null")
    mock_serial = MagicMock()
    mock_serial.is_open = True
    mock_serial.in_waiting = 0
    mock_serial.read.return_value = b"41 0C 1A F8\r\n>"
    c.connection = mock_serial
    # send_command writes and reads
    mock_serial.in_waiting = 0  # so while loop exits immediately
    # We just need no exception; actual response depends on in_waiting
    with patch("time.sleep"):
        result = c.send_command("010C")
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# 2. obd/commands.py
# ---------------------------------------------------------------------------

def test_parse_rpm():
    from obd.commands import parse_response
    # A=0x1A, B=0xF8 → (26*256 + 248) / 4 = 6904/4 = 1726.0
    result = parse_response("010C", "41 0C 1A F8")
    assert result == pytest.approx(1726.0)


def test_parse_speed():
    from obd.commands import parse_response
    # A=0x64 = 100 km/h
    result = parse_response("010D", "41 0D 64")
    assert result == pytest.approx(100.0)


def test_parse_coolant_temp():
    from obd.commands import parse_response
    # A=0x7D = 125 → 125-40 = 85°C
    result = parse_response("0105", "41 05 7D")
    assert result == pytest.approx(85.0)


def test_parse_throttle():
    from obd.commands import parse_response
    # A=0x80=128 → 128*100/255 ≈ 50.2%
    result = parse_response("0111", "41 11 80")
    assert result == pytest.approx(50.2, abs=0.5)


def test_parse_maf():
    from obd.commands import parse_response
    # A=0x03, B=0xE8 = 1000 → 1000/100 = 10.0 g/s
    result = parse_response("0110", "41 10 03 E8")
    assert result == pytest.approx(10.0)


def test_parse_timing():
    from obd.commands import parse_response
    # A=0x80=128 → (128/2)-64 = 0°
    result = parse_response("010E", "41 0E 80")
    assert result == pytest.approx(0.0)


def test_parse_bad_response():
    from obd.commands import parse_response
    result = parse_response("010C", "NO DATA")
    assert result is None


def test_obd2commands_all_names():
    from obd.commands import OBD2Commands
    names = OBD2Commands.all_names()
    assert "rpm" in names
    assert "speed" in names
    assert len(names) >= 9


# ---------------------------------------------------------------------------
# 3. obd/reader.py
# ---------------------------------------------------------------------------

def test_reader_read_pid():
    from obd.reader import OBD2Reader
    conn = make_mock_connector("41 0D 3C")  # speed = 60 km/h
    reader = OBD2Reader(conn)
    result = reader.read_pid("010D")
    assert result["pid"] == "010D"
    assert result["error"] is None


def test_reader_read_sensor_unknown():
    from obd.reader import OBD2Reader
    conn = make_mock_connector()
    reader = OBD2Reader(conn)
    result = reader.read_sensor("nonexistent_sensor")
    assert result["error"] is not None


def test_reader_read_all_sensors():
    from obd.reader import OBD2Reader
    conn = make_mock_connector("41 0C 1A F8")
    reader = OBD2Reader(conn)
    data = reader.read_all_sensors()
    assert isinstance(data, dict)
    assert "rpm" in data
    assert "speed" in data


def test_reader_parse_dtc():
    from obd.reader import OBD2Reader
    # "43 01 30 00" → P0300 (Type P, code 0x0300=768 → "P0768")
    # Actually: high=0x01, low=0x30
    # dtype = (0x01 >> 6) & 3 = 0  → P
    # num = (0x01 & 0x3F) << 8 | 0x30 = 0x0130 = 304
    # → P0304
    codes = OBD2Reader._parse_dtc("43 01 30 00")
    assert len(codes) >= 1
    assert codes[0].startswith("P")


def test_reader_parse_dtc_empty():
    from obd.reader import OBD2Reader
    codes = OBD2Reader._parse_dtc("43 00 00 00 00")
    assert codes == []


def test_reader_read_dtc_error_handling():
    from obd.reader import OBD2Reader
    conn = MagicMock()
    conn.send_command.side_effect = ConnectionError("not connected")
    reader = OBD2Reader(conn)
    codes = reader.read_dtc()
    assert codes == []


# ---------------------------------------------------------------------------
# 4. obd/writer.py
# ---------------------------------------------------------------------------

def test_writer_send_raw():
    from obd.writer import OBD2Writer
    conn = make_mock_connector("OK")
    writer = OBD2Writer(conn)
    result = writer.send_raw("AT Z")
    assert result == "OK"


def test_writer_clear_dtc_success():
    from obd.writer import OBD2Writer
    conn = make_mock_connector("44")
    writer = OBD2Writer(conn)
    assert writer.clear_dtc() is True


def test_writer_clear_dtc_failure():
    from obd.writer import OBD2Writer
    conn = make_mock_connector("NO DATA")
    writer = OBD2Writer(conn)
    assert writer.clear_dtc() is False


def test_writer_set_protocol():
    from obd.writer import OBD2Writer
    conn = make_mock_connector("OK")
    writer = OBD2Writer(conn)
    result = writer.set_protocol(6)
    conn.send_command.assert_called_with("AT SP 6")
    assert result == "OK"


# ---------------------------------------------------------------------------
# 5. utils/export.py
# ---------------------------------------------------------------------------

def test_csv_exporter_basic():
    from utils.export import CSVExporter
    data = {
        "rpm":   {"value": 1500.0, "unit": "rpm",  "error": None},
        "speed": {"value": 60.0,   "unit": "km/h", "error": None},
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        fname = os.path.join(tmpdir, "test_export.csv")
        result = CSVExporter().export(data, fname)
        assert result == fname
        with open(fname, newline="") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 2
        sensors = {r["sensor"] for r in rows}
        assert "rpm" in sensors
        assert "speed" in sensors


def test_csv_exporter_default_filename():
    from utils.export import CSVExporter
    data = {"rpm": {"value": 800.0, "unit": "rpm", "error": None}}
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            fname = CSVExporter().export(data)
            assert os.path.exists(fname)
            assert "obd2_data_" in os.path.basename(fname)
        finally:
            os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# 6. Flask API (demo mode)
# ---------------------------------------------------------------------------

@pytest.fixture()
def flask_client():
    from web.app import create_app
    app = create_app(demo=True)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_flask_index(flask_client):
    r = flask_client.get("/")
    assert r.status_code == 200
    assert b"OBD2" in r.data


def test_flask_api_status(flask_client):
    r = flask_client.get("/api/status")
    assert r.status_code == 200
    d = r.get_json()
    assert d["connected"] is True
    assert d["mode"] == "demo"


def test_flask_api_sensors(flask_client):
    r = flask_client.get("/api/sensors")
    assert r.status_code == 200
    d = r.get_json()
    assert "sensors" in d
    assert "rpm" in d["sensors"]


def test_flask_api_dtc(flask_client):
    r = flask_client.get("/api/dtc")
    assert r.status_code == 200
    d = r.get_json()
    assert "codes" in d


def test_flask_api_dtc_clear(flask_client):
    r = flask_client.post("/api/dtc/clear")
    assert r.status_code == 200
    d = r.get_json()
    assert d["success"] is True


def test_flask_api_command(flask_client):
    r = flask_client.post("/api/command",
                          data=json.dumps({"command": "AT RV"}),
                          content_type="application/json")
    assert r.status_code == 200
    d = r.get_json()
    assert "response" in d


def test_flask_api_command_empty(flask_client):
    r = flask_client.post("/api/command",
                          data=json.dumps({}),
                          content_type="application/json")
    assert r.status_code == 400


def test_flask_api_export(flask_client):
    r = flask_client.get("/api/export")
    assert r.status_code == 200
    assert r.content_type == "text/csv; charset=utf-8"
    lines = r.data.decode().splitlines()
    assert lines[0].startswith("timestamp,sensor")
