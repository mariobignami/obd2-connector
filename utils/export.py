"""CSV export utility for OBD2 sensor readings."""

import csv
import os
from datetime import datetime


class CSVExporter:
    """Export OBD2 sensor data to a CSV file."""

    def export(self, data: dict, filename: str = None) -> str:
        """Export *data* to a CSV file.

        Parameters
        ----------
        data:
            Dict of ``{sensor_name: {"value": ..., "unit": ..., "error": ...}}``.
        filename:
            Optional output path.  Defaults to ``obd2_data_{timestamp}.csv``
            in the current working directory.

        Returns
        -------
        str
            Absolute path to the written file.
        """
        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"obd2_data_{ts}.csv"

        filename = os.path.abspath(filename)
        timestamp = datetime.now().isoformat()

        with open(filename, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["timestamp", "sensor", "value", "unit", "error"])
            for name, info in data.items():
                writer.writerow([
                    timestamp,
                    name,
                    info.get("value", ""),
                    info.get("unit", ""),
                    info.get("error", ""),
                ])

        return filename
