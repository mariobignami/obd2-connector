"""
CSV and JSON export utilities.
"""

import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


def _default_filename(ext: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"obd2_export_{ts}.{ext}"


def export_csv(
    data: Dict[str, Any],
    path: Optional[str] = None,
    pid_info: Optional[Dict] = None,
    append: bool = False,
) -> str:
    """
    Export a single snapshot dict to a CSV file.

    Parameters
    ----------
    data      : dict produced by OBDReader.read_all() or a realtime callback
    path      : output file path (auto-generated if None)
    pid_info  : OBD_PIDS dict used to add description/unit columns
    append    : if True and file exists, append a row without re-writing header

    Returns the path of the written file.
    """
    if path is None:
        path = _default_filename("csv")

    timestamp = data.get("_timestamp")
    row = {"timestamp": datetime.fromtimestamp(timestamp).isoformat() if timestamp else datetime.now().isoformat()}

    for key, value in data.items():
        if key.startswith("_"):
            continue
        row[key] = "" if value is None else value

    file_exists = os.path.isfile(path)
    mode = "a" if append and file_exists else "w"
    with open(path, mode, newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row.keys()))
        if not (append and file_exists):
            writer.writeheader()
        writer.writerow(row)

    return path


def export_csv_log(
    rows: List[Dict[str, Any]],
    path: Optional[str] = None,
) -> str:
    """
    Export a list of snapshot dicts (a session log) to CSV.

    Returns the path of the written file.
    """
    if not rows:
        raise ValueError("No data to export.")

    if path is None:
        path = _default_filename("csv")

    # Build unified column set
    columns = ["timestamp"]
    for row in rows:
        for key in row:
            if not key.startswith("_") and key not in columns:
                columns.append(key)

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            ts = row.get("_timestamp")
            out = {"timestamp": datetime.fromtimestamp(ts).isoformat() if ts else ""}
            for key, val in row.items():
                if key.startswith("_"):
                    continue
                out[key] = "" if val is None else val
            writer.writerow(out)

    return path


def export_json(
    data: Any,
    path: Optional[str] = None,
    indent: int = 2,
) -> str:
    """
    Export data (dict or list) to a JSON file.

    Returns the path of the written file.
    """
    if path is None:
        path = _default_filename("json")

    # Replace None with null-safe serialisable form
    def _default(obj):
        return str(obj)

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=indent, default=_default, ensure_ascii=False)

    return path
