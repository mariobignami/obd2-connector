"""OBD2 PID definitions, AT commands, and response parsing."""

# ---------------------------------------------------------------------------
# Parse helpers
# ---------------------------------------------------------------------------

def _rpm(a, b):
    return ((a * 256) + b) / 4.0

def _speed(a, _b=None):
    return float(a)

def _temp(a, _b=None):
    return float(a - 40)

def _percent(a, _b=None):
    return round(a * 100.0 / 255.0, 1)

def _maf(a, b):
    return ((a * 256) + b) / 100.0

def _timing(a, _b=None):
    return (a / 2.0) - 64.0


# ---------------------------------------------------------------------------
# Sensor PID table
# name → (pid_hex, description, unit, parse_fn)
# ---------------------------------------------------------------------------

SENSOR_PIDS = {
    "rpm":          ("010C", "Engine RPM",            "rpm",  _rpm),
    "speed":        ("010D", "Vehicle Speed",          "km/h", _speed),
    "coolant_temp": ("0105", "Coolant Temperature",    "°C",   _temp),
    "throttle":     ("0111", "Throttle Position",      "%",    _percent),
    "engine_load":  ("0104", "Engine Load",            "%",    _percent),
    "fuel_level":   ("012F", "Fuel Level",             "%",    _percent),
    "intake_temp":  ("010F", "Intake Air Temperature", "°C",   _temp),
    "maf":          ("0110", "Mass Air Flow",          "g/s",  _maf),
    "timing":       ("010E", "Timing Advance",         "°",    _timing),
}

# ---------------------------------------------------------------------------
# AT commands for ELM327 initialisation
# ---------------------------------------------------------------------------

AT_COMMANDS = {
    "reset":          "AT Z",
    "echo_off":       "AT E0",
    "linefeeds_off":  "AT L0",
    "headers_off":    "AT H0",
    "auto_protocol":  "AT SP 0",
    "describe_proto": "AT DP",
    "read_voltage":   "AT RV",
}


# ---------------------------------------------------------------------------
# Public parse_response function
# ---------------------------------------------------------------------------

def _hex_bytes(raw: str) -> list:
    """Return a list of integer byte values from a hex response string."""
    clean = raw.replace("\r", " ").replace("\n", " ").replace(">", "").strip()
    tokens = clean.split()
    return [int(t, 16) for t in tokens if len(t) == 2 and all(c in "0123456789abcdefABCDEF" for c in t)]


def parse_response(pid: str, raw: str):
    """Parse a raw hex OBD2 response string into a numeric value.

    Parameters
    ----------
    pid:
        The 4-character PID string used in the request (e.g. ``"010C"``).
    raw:
        The raw hex string returned by the adapter (e.g. ``"41 0C 1A F8"``).

    Returns
    -------
    float | None
        Parsed numeric value, or ``None`` on parse failure.
    """
    try:
        bytes_list = _hex_bytes(raw)
        if len(bytes_list) < 2:
            return None

        # Drop the echo header bytes (41 XX …)
        # The first byte should be 0x41 (positive response to 01 mode)
        if bytes_list[0] == 0x41:
            bytes_list = bytes_list[2:]  # skip 41 and PID byte

        if not bytes_list:
            return None

        pid_upper = pid.upper()

        # Look up by the raw PID nibbles
        pid_map = {v[0].upper(): v[3] for v in SENSOR_PIDS.values()}
        parse_fn = pid_map.get(pid_upper)
        if parse_fn is None:
            return None

        a = bytes_list[0]
        b = bytes_list[1] if len(bytes_list) > 1 else 0
        return parse_fn(a, b)
    except Exception:
        return None


class OBD2Commands:
    """Namespace exposing PID and AT command data."""

    SENSOR_PIDS = SENSOR_PIDS
    AT_COMMANDS = AT_COMMANDS

    @staticmethod
    def parse_response(pid: str, raw: str):
        return parse_response(pid, raw)

    @staticmethod
    def get_pid(name: str):
        """Return (pid_hex, description, unit) for a sensor name or None."""
        entry = SENSOR_PIDS.get(name)
        if entry:
            return entry[0], entry[1], entry[2]
        return None

    @staticmethod
    def all_names():
        return list(SENSOR_PIDS.keys())
