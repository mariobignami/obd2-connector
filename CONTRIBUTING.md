# 🤝 Contributing to OBD2 Connector

Thank you for your interest in contributing! This guide explains how to set up the development environment, run tests, and submit changes.

---

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Code Conventions](#code-conventions)
- [Adding New OBD-II PIDs](#adding-new-obd-ii-pids)
- [Submitting a Pull Request](#submitting-a-pull-request)

---

## Getting Started

### Prerequisites

- Python 3.8 or newer
- An ELM327 adapter is **not** required for development — all tests use stubs.

### Installation

```bash
git clone https://github.com/mariobignami/obd2-connector.git
cd obd2-connector
pip install -r requirements.txt
```

### Verify the setup

```bash
python -m pytest tests/ -v
```

All tests should pass without any hardware connected.

---

## Project Structure

```
obd2-connector/
├── main.py                  # CLI entry point (Click)
├── connector/
│   ├── base.py              # Abstract BaseConnector (serial I/O + AT init)
│   ├── bluetooth.py         # BluetoothConnector (rfcomm / COM)
│   └── serial_conn.py       # SerialConnector (USB/Serial)
├── obd/
│   ├── commands.py          # OBD_PIDS table, AT_COMMANDS, parsers
│   ├── reader.py            # OBDReader – read PIDs, DTCs, VIN, real-time
│   └── writer.py            # OBDWriter – raw commands, protocol, timeout
├── cli/
│   └── interface.py         # Rich terminal dashboard + interactive REPL
├── web/
│   ├── app.py               # Flask app factory (REST API + SSE streaming)
│   └── templates/
│       └── index.html       # Browser dashboard (gauges, DTCs, terminal)
├── utils/
│   └── export.py            # CSV / JSON export helpers
├── tests/
│   └── test_obd2.py         # Unit tests (no hardware required)
├── requirements.txt
└── README.md
```

---

## Running Tests

The test suite is hardware-free and uses stub connectors:

```bash
python -m pytest tests/ -v
```

To run a specific test class or function:

```bash
python -m pytest tests/ -v -k "TestCommands"
python -m pytest tests/ -v -k "test_rpm_parse"
```

### Writing new tests

- Place tests in `tests/test_obd2.py` (or a new file under `tests/`).
- Use `_StubConnector` (already defined in the test file) to simulate hardware responses.
- Tests must not depend on real serial ports, Bluetooth adapters, or network access.

Example stub usage:

```python
from tests.test_obd2 import _StubConnector
from obd.reader import OBDReader

def test_my_feature():
    stub = _StubConnector(response="41 0C 0B B8")
    reader = OBDReader(stub)
    assert reader.read_pid("RPM") == pytest.approx(748.0)
```

---

## Code Conventions

- **Python version**: 3.8+ compatible syntax.
- **Style**: PEP 8, 4-space indentation, type hints on all public methods.
- **Imports**: use relative imports within packages (e.g. `from .base import BaseConnector`).
- **Error messages**: follow the `[COMPONENT][ERROR] message` prefix pattern
  (e.g. `[BT][ERROR] Could not open port`).
- **No linter config** is enforced — match the existing style.
- **Docstrings**: add docstrings to all new public classes and methods.

### Connector classes

All connectors must subclass `BaseConnector` and implement:

```python
def connect(self) -> bool: ...
```

`initialize()` must always call (in order):
`reset()` → `echo_off()` → `linefeeds_off()` → `headers_off()` → `spaces_off()` → `set_auto_protocol()`

### Adding a new CLI command

1. Add the handler branch in `CLIInterface.run_interactive()` (`cli/interface.py`).
2. Add a short description to the `commands` list inside `_print_help()`.
3. Add a detailed entry to the `_COMMAND_HELP` class attribute.
4. Add a test that exercises the new command with a stub connector.

---

## Adding New OBD-II PIDs

Edit `obd/commands.py` and add a new entry to `OBD_PIDS`:

```python
"MY_PID": {
    "desc":       "Human-readable sensor name",
    "mode":       "01",          # OBD-II mode (string)
    "pid":        "XX",          # PID hex code (string, two chars)
    "bytes":      2,             # Number of data bytes expected
    "unit":       "unit_string", # Display unit (empty string if dimensionless)
    "parse":      lambda b: ..., # Callable[[list[int]], float|int|None]
    # Optional alert thresholds (used for colour-coding in the dashboard):
    "alert_high": 120,           # Value >= this → red warning
    "alert_low":  10,            # Value <= this → yellow warning
},
```

After adding a PID:
1. Add a `test_<pid>_parse` test in `tests/test_obd2.py`.
2. If the PID returns a non-scalar value (like `MIL_STATUS`), add it to the exclusion
   lists in `obd/reader.py` (`read_all`) and `cli/interface.py` (`scan_all`, `_build_dashboard`, `show_freeze_frame`).

---

## Submitting a Pull Request

1. Fork the repository and create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```
2. Make your changes and ensure all tests pass:
   ```bash
   python -m pytest tests/ -v
   ```
3. Open a pull request against the `main` branch with a clear description of what
   was changed and why.
4. Link any related issue in the PR description.

---

## ❓ Questions

Open an issue on GitHub if you have questions about the codebase or the contribution process.
