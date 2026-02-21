"""
OBD2 PID definitions and AT command constants.

Each PID entry is a dict with:
  - desc    : human-readable description
  - mode    : OBD mode (01 = live data, 09 = vehicle info, …)
  - pid     : 2-hex-digit PID byte
  - bytes   : number of data bytes in the response
  - parse   : callable(bytes_list) -> numeric value
  - unit    : display unit string
  - min/max : expected value range (used for alert thresholds)
"""

from typing import Callable, Dict, Any

# ---------------------------------------------------------------------------
# Helper parsers
# ---------------------------------------------------------------------------

def _a(b):                 return b[0]
def _ab(b):                return (b[0] * 256 + b[1])
def _rpm(b):               return (b[0] * 256 + b[1]) / 4
def _temp(b):              return b[0] - 40
def _percent_a(b):         return round(b[0] * 100 / 255, 1)
def _percent_ab(b):        return round((b[0] * 256 + b[1]) * 100 / 65535, 1)
def _maf(b):               return round((b[0] * 256 + b[1]) / 100, 2)
def _timing(b):            return b[0] / 2 - 64
def _voltage(b):           return round((b[0] * 256 + b[1]) / 1000, 3)
def _fuel_rate(b):         return round((b[0] * 256 + b[1]) * 0.05, 2)
def _short_fuel_trim(b):   return round((b[0] - 128) * 100 / 128, 1)
def _long_fuel_trim(b):    return round((b[0] - 128) * 100 / 128, 1)
def _equiv_ratio(b):       return round((b[0] * 256 + b[1]) * 0.0000305, 4)
def _evap_pressure(b):     # signed 16-bit, Pa
    val = b[0] * 256 + b[1]
    if val >= 32768:
        val -= 65536
    return round(val / 4, 2)


# ---------------------------------------------------------------------------
# PID table  (Mode 01 – live data)
# ---------------------------------------------------------------------------

OBD_PIDS: Dict[str, Dict[str, Any]] = {
    # --- Status ---
    "MIL_STATUS": {
        "desc": "MIL / Monitor Status",
        "mode": "01",
        "pid": "01",
        "bytes": 4,
        "parse": lambda b: {"mil_on": bool(b[0] & 0x80), "dtc_count": b[0] & 0x7F},
        "unit": "",
        "min": 0,
        "max": 1,
    },
    # --- Engine ---
    "RPM": {
        "desc": "Engine RPM",
        "mode": "01",
        "pid": "0C",
        "bytes": 2,
        "parse": _rpm,
        "unit": "rpm",
        "min": 0,
        "max": 8000,
        "alert_high": 6500,
    },
    "SPEED": {
        "desc": "Vehicle Speed",
        "mode": "01",
        "pid": "0D",
        "bytes": 1,
        "parse": _a,
        "unit": "km/h",
        "min": 0,
        "max": 280,
        "alert_high": 200,
    },
    "COOLANT_TEMP": {
        "desc": "Engine Coolant Temperature",
        "mode": "01",
        "pid": "05",
        "bytes": 1,
        "parse": _temp,
        "unit": "°C",
        "min": -40,
        "max": 215,
        "alert_high": 105,
    },
    "ENGINE_LOAD": {
        "desc": "Calculated Engine Load",
        "mode": "01",
        "pid": "04",
        "bytes": 1,
        "parse": _percent_a,
        "unit": "%",
        "min": 0,
        "max": 100,
        "alert_high": 95,
    },
    "THROTTLE": {
        "desc": "Throttle Position",
        "mode": "01",
        "pid": "11",
        "bytes": 1,
        "parse": _percent_a,
        "unit": "%",
        "min": 0,
        "max": 100,
    },
    "MAF": {
        "desc": "Mass Air Flow Rate",
        "mode": "01",
        "pid": "10",
        "bytes": 2,
        "parse": _maf,
        "unit": "g/s",
        "min": 0,
        "max": 655,
    },
    "INTAKE_TEMP": {
        "desc": "Intake Air Temperature",
        "mode": "01",
        "pid": "0F",
        "bytes": 1,
        "parse": _temp,
        "unit": "°C",
        "min": -40,
        "max": 215,
        "alert_high": 60,
    },
    "MAP": {
        "desc": "Intake Manifold Absolute Pressure",
        "mode": "01",
        "pid": "0B",
        "bytes": 1,
        "parse": _a,
        "unit": "kPa",
        "min": 0,
        "max": 255,
    },
    "TIMING_ADVANCE": {
        "desc": "Timing Advance",
        "mode": "01",
        "pid": "0E",
        "bytes": 1,
        "parse": _timing,
        "unit": "° before TDC",
        "min": -64,
        "max": 63.5,
    },
    "OIL_TEMP": {
        "desc": "Engine Oil Temperature",
        "mode": "01",
        "pid": "5C",
        "bytes": 1,
        "parse": _temp,
        "unit": "°C",
        "min": -40,
        "max": 215,
        "alert_high": 130,
    },
    # --- Fuel ---
    "FUEL_LEVEL": {
        "desc": "Fuel Tank Level",
        "mode": "01",
        "pid": "2F",
        "bytes": 1,
        "parse": _percent_a,
        "unit": "%",
        "min": 0,
        "max": 100,
        "alert_low": 10,
    },
    "FUEL_RATE": {
        "desc": "Engine Fuel Rate",
        "mode": "01",
        "pid": "5E",
        "bytes": 2,
        "parse": _fuel_rate,
        "unit": "L/h",
        "min": 0,
        "max": 3276.75,
    },
    "SHORT_FUEL_TRIM_1": {
        "desc": "Short Term Fuel Trim (Bank 1)",
        "mode": "01",
        "pid": "06",
        "bytes": 1,
        "parse": _short_fuel_trim,
        "unit": "%",
        "min": -100,
        "max": 99.2,
    },
    "LONG_FUEL_TRIM_1": {
        "desc": "Long Term Fuel Trim (Bank 1)",
        "mode": "01",
        "pid": "07",
        "bytes": 1,
        "parse": _long_fuel_trim,
        "unit": "%",
        "min": -100,
        "max": 99.2,
    },
    # --- Electrical ---
    "VOLTAGE": {
        "desc": "Control Module Voltage",
        "mode": "01",
        "pid": "42",
        "bytes": 2,
        "parse": _voltage,
        "unit": "V",
        "min": 0,
        "max": 65.535,
        "alert_low": 11.5,
    },
    # --- Atmosphere ---
    "BARO_PRESSURE": {
        "desc": "Barometric Pressure",
        "mode": "01",
        "pid": "33",
        "bytes": 1,
        "parse": _a,
        "unit": "kPa",
        "min": 0,
        "max": 255,
    },
    "AMBIENT_TEMP": {
        "desc": "Ambient Air Temperature",
        "mode": "01",
        "pid": "46",
        "bytes": 1,
        "parse": _temp,
        "unit": "°C",
        "min": -40,
        "max": 215,
    },
    # --- Trip / Run-time ---
    "RUNTIME": {
        "desc": "Engine Run Time",
        "mode": "01",
        "pid": "1F",
        "bytes": 2,
        "parse": _ab,
        "unit": "s",
        "min": 0,
        "max": 65535,
    },
    "DISTANCE_MIL": {
        "desc": "Distance Traveled with MIL On",
        "mode": "01",
        "pid": "21",
        "bytes": 2,
        "parse": _ab,
        "unit": "km",
        "min": 0,
        "max": 65535,
    },
    "DISTANCE_SINCE_CLR": {
        "desc": "Distance Since DTCs Cleared",
        "mode": "01",
        "pid": "31",
        "bytes": 2,
        "parse": _ab,
        "unit": "km",
        "min": 0,
        "max": 65535,
    },
    "WARMUPS_SINCE_CLR": {
        "desc": "Warm-ups Since DTCs Cleared",
        "mode": "01",
        "pid": "30",
        "bytes": 1,
        "parse": _a,
        "unit": "count",
        "min": 0,
        "max": 255,
    },
    "ABS_LOAD": {
        "desc": "Absolute Load Value (volumetric efficiency)",
        "mode": "01",
        "pid": "43",
        "bytes": 2,
        "parse": _percent_ab,
        "unit": "%",
        "min": 0,
        "max": 100,
    },
    "EVAP_PRESSURE": {
        "desc": "Evap System Vapor Pressure",
        "mode": "01",
        "pid": "32",
        "bytes": 2,
        "parse": _evap_pressure,
        "unit": "Pa",
        "min": -8192,
        "max": 8192,
    },
}

# ---------------------------------------------------------------------------
# Mode 09 – Vehicle information PIDs
# ---------------------------------------------------------------------------

VEHICLE_INFO_PIDS: Dict[str, Dict[str, Any]] = {
    "VIN": {
        "desc": "Vehicle Identification Number",
        "mode": "09",
        "pid": "02",
    },
    "ECU_NAME": {
        "desc": "ECU Name",
        "mode": "09",
        "pid": "0A",
    },
    "CALIBRATION_ID": {
        "desc": "Calibration ID",
        "mode": "09",
        "pid": "04",
    },
}

# ---------------------------------------------------------------------------
# AT command constants
# ---------------------------------------------------------------------------

AT_COMMANDS = {
    "RESET": "AT Z",
    "ECHO_OFF": "AT E0",
    "ECHO_ON": "AT E1",
    "LINEFEEDS_OFF": "AT L0",
    "LINEFEEDS_ON": "AT L1",
    "HEADERS_OFF": "AT H0",
    "HEADERS_ON": "AT H1",
    "AUTO_PROTOCOL": "AT SP 0",
    "PROTOCOL_CAN": "AT SP 6",
    "DESCRIBE_PROTOCOL": "AT DP",
    "DESCRIBE_PROTOCOL_NUM": "AT DPN",
    "VOLTAGE": "AT RV",
    "DEVICE_DESCRIPTION": "AT @1",
    "DEVICE_ID": "AT @2",
    "VERSION": "AT I",
    "SPACES_OFF": "AT S0",
    "SPACES_ON": "AT S1",
    "ALLOW_LONG": "AT AL",
    "ADAPTIVE_TIMING_OFF": "AT AT0",
    "ADAPTIVE_TIMING_1": "AT AT1",
    "ADAPTIVE_TIMING_2": "AT AT2",
    "SLOW_INIT": "AT SI",
    "FAST_INIT": "AT FI",
    "WAKEUP_MSG_OFF": "AT WM",
}

# ---------------------------------------------------------------------------
# DTC prefix lookup (first character of DTC code)
# ---------------------------------------------------------------------------

DTC_PREFIXES = {
    "0": "P0 – Powertrain (generic)",
    "1": "P1 – Powertrain (manufacturer)",
    "2": "P2 – Powertrain (generic)",
    "3": "P3 – Powertrain (manufacturer)",
    "4": "C0 – Chassis (generic)",
    "5": "C1 – Chassis (manufacturer)",
    "6": "C2 – Chassis (manufacturer)",
    "7": "C3 – Chassis (manufacturer)",
    "8": "B0 – Body (generic)",
    "9": "B1 – Body (manufacturer)",
    "A": "B2 – Body (manufacturer)",
    "B": "B3 – Body (manufacturer)",
    "C": "U0 – Network (generic)",
    "D": "U1 – Network (manufacturer)",
    "E": "U2 – Network (manufacturer)",
    "F": "U3 – Network (manufacturer)",
}
