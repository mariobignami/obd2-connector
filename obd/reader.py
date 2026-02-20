"""OBD2Reader — high-level sensor and DTC reading."""

from .commands import SENSOR_PIDS, parse_response


class OBD2Reader:
    """Read sensor data and DTC codes via a BaseConnector."""

    def __init__(self, connector):
        self.connector = connector

    # ------------------------------------------------------------------
    # PID reading
    # ------------------------------------------------------------------

    def read_pid(self, pid: str) -> dict:
        """Send *pid* and return a result dict.

        Returns
        -------
        dict with keys: pid, raw, value, unit, error
        """
        result = {"pid": pid, "raw": None, "value": None, "unit": None, "error": None}
        try:
            raw = self.connector.send_command(pid)
            result["raw"] = raw
            value = parse_response(pid, raw)
            result["value"] = value
        except Exception as exc:
            result["error"] = str(exc)
        return result

    def read_sensor(self, name: str) -> dict:
        """Read a sensor by its friendly *name* (e.g. ``"rpm"``).

        Returns the same dict as :meth:`read_pid` plus a ``"name"`` key.
        """
        entry = SENSOR_PIDS.get(name)
        if entry is None:
            return {"name": name, "pid": None, "raw": None, "value": None,
                    "unit": None, "error": f"Unknown sensor: {name}"}
        pid, _desc, unit, _fn = entry
        result = self.read_pid(pid)
        result["name"] = name
        result["unit"] = unit
        return result

    def read_all_sensors(self) -> dict:
        """Read every sensor in SENSOR_PIDS.

        Returns
        -------
        dict
            ``{name: {"value": ..., "unit": ..., "error": ...}, ...}``
        """
        results = {}
        for name in SENSOR_PIDS:
            r = self.read_sensor(name)
            results[name] = {
                "value": r["value"],
                "unit":  r["unit"],
                "error": r["error"],
            }
        return results

    # ------------------------------------------------------------------
    # DTC reading
    # ------------------------------------------------------------------

    def read_dtc(self) -> list:
        """Send Mode 03 and return a list of DTC code strings like ``"P0300"``."""
        try:
            raw = self.connector.send_command("03")
            return self._parse_dtc(raw)
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_dtc(raw: str) -> list:
        """Parse a raw Mode-03 response into DTC code strings.

        Response format example: ``"43 01 30 00 00 00 00"``
        Each 2-byte pair (after the ``43`` header) is one DTC.
        """
        _TYPE = {0: "P", 1: "C", 2: "B", 3: "U"}
        codes = []
        try:
            tokens = raw.replace("\r", " ").replace(">", "").split()
            # Drop '43' header byte if present
            if tokens and tokens[0].upper() == "43":
                tokens = tokens[1:]
            # Process pairs
            i = 0
            while i + 1 < len(tokens):
                high = int(tokens[i], 16)
                low  = int(tokens[i + 1], 16)
                i += 2
                if high == 0 and low == 0:
                    continue
                dtype = (high >> 6) & 0x03
                num   = ((high & 0x3F) << 8) | low
                code  = f"{_TYPE[dtype]}{num:04d}"
                codes.append(code)
        except Exception:
            pass
        return codes
