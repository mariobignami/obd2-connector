# Copilot Instructions for obd2-connector

## Project Summary

`obd2-connector` is a Python library for communicating with vehicles via OBD2 adapters (ELM327) over Bluetooth or USB/Serial. It provides a clean, object-oriented API for sending AT and OBD2 commands, reading sensor data, and managing diagnostic trouble codes (DTCs).

## Language & Runtime

- **Language:** Python 3.8+
- **Runtime used in CI/sandbox:** Python 3.12

## Project Layout

```
obd2-connector/
├── .github/
│   └── copilot-instructions.md   # This file
├── connector/                     # Main package (only implemented module so far)
│   ├── __init__.py                # Exports BluetoothConnector, SerialConnector
│   ├── base.py                    # Abstract BaseConnector class
│   ├── bluetooth.py               # BluetoothConnector (ELM327 via rfcomm/COM port)
│   └── serial_conn.py             # SerialConnector (USB/Serial ELM327)
├── requirements.txt               # Runtime dependencies
├── README.md                      # Project documentation (Portuguese)
└── .gitignore
```

> **Note:** The README describes additional modules (`obd/`, `cli/`, `utils/`, `main.py`) that are **not yet implemented**. When adding new features, place them in the appropriate module as described in the README.

## Architecture

- `BaseConnector` (abstract, `connector/base.py`): wraps `pyserial`, handles `send_command`, `initialize`, `reset`, `echo_off`, `linefeeds_off`, `set_auto_protocol`. All communication with the ELM327 adapter goes through `send_command`.
- `BluetoothConnector` (`connector/bluetooth.py`): extends `BaseConnector` for Bluetooth (rfcomm/COM) connections. Includes `list_bluetooth_ports()` static helper.
- `SerialConnector` (`connector/serial_conn.py`): extends `BaseConnector` for USB/Serial connections. Includes `list_serial_ports()` static helper.

## Bootstrap & Dependency Installation

```bash
pip install -r requirements.txt
```

Dependencies: `pyserial>=3.5`, `obd>=0.7.1`, `rich>=13.0.0`, `click>=8.1.0`.

## Testing

There is **no test suite** in the repository yet. When adding tests:

- Use `pytest` as the test runner.
- Place tests in a `tests/` directory at the repo root.
- Real hardware is not available in CI; use stub/mock connectors (subclass `BaseConnector` and mock the `serial.Serial` connection).
- Run tests with: `python -m pytest tests/ -v`

## Key Conventions

- All connector classes subclass `BaseConnector` and must implement `connect() -> bool`.
- `send_command(command: str) -> str` strips the command, appends `\r`, writes to the serial port, waits 300 ms, then reads all available bytes.
- `initialize()` always calls `reset()`, `echo_off()`, `linefeeds_off()`, `set_auto_protocol()` in that order.
- Error messages use the prefix pattern `[COMPONENT][ERROR] message` (e.g., `[BT][ERROR]`, `[USB][ERROR]`).
- Imports: use relative imports within the `connector` package (e.g., `from .base import BaseConnector`).
- No linter or formatter is configured; match the existing style (PEP 8, 4-space indentation, type hints on public methods).
