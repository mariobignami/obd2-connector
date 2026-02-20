"""Flask web application for the OBD2 dashboard."""

import io
import json
import math
import time
import random
import threading
from datetime import datetime

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

# ---------------------------------------------------------------------------
# Demo data generator
# ---------------------------------------------------------------------------

_demo_tick = 0
_demo_lock = threading.Lock()


def _demo_sensors():
    """Return simulated sensor readings that vary over time."""
    global _demo_tick
    with _demo_lock:
        _demo_tick += 1
    t = _demo_tick * 0.15
    return {
        "rpm":          {"value": round(800 + 1350 * (1 + math.sin(t)) + random.uniform(-50, 50), 1),
                         "unit": "rpm",   "error": None},
        "speed":        {"value": round(max(0, 60 + 50 * math.sin(t * 0.4) + random.uniform(-3, 3)), 1),
                         "unit": "km/h",  "error": None},
        "coolant_temp": {"value": round(90 + 3 * math.sin(t * 0.1) + random.uniform(-0.5, 0.5), 1),
                         "unit": "°C",    "error": None},
        "throttle":     {"value": round(max(5, min(95, 35 + 25 * math.sin(t * 0.5) + random.uniform(-2, 2))), 1),
                         "unit": "%",     "error": None},
        "engine_load":  {"value": round(max(10, min(90, 40 + 20 * math.sin(t * 0.3) + random.uniform(-2, 2))), 1),
                         "unit": "%",     "error": None},
        "fuel_level":   {"value": 65.0,   "unit": "%",     "error": None},
        "intake_temp":  {"value": round(28 + 4 * math.sin(t * 0.08) + random.uniform(-0.5, 0.5), 1),
                         "unit": "°C",    "error": None},
        "maf":          {"value": round(max(2, 9 + 4 * math.sin(t * 0.6) + random.uniform(-0.3, 0.3)), 2),
                         "unit": "g/s",   "error": None},
        "timing":       {"value": round(12 + 6 * math.sin(t * 0.2) + random.uniform(-0.5, 0.5), 1),
                         "unit": "°",     "error": None},
    }


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(connector=None, reader=None, writer=None, demo=False):
    """Create and return the Flask application.

    Parameters
    ----------
    connector, reader, writer:
        Live OBD2 objects.  When *demo* is True these may all be None.
    demo:
        When True the app generates simulated data instead of querying
        real hardware.
    """
    app = Flask(__name__, template_folder="templates")
    app.config["DEMO"] = demo
    app.config["CONNECTOR"] = connector
    app.config["READER"] = reader
    app.config["WRITER"] = writer

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_sensors():
        if app.config["DEMO"] or app.config["READER"] is None:
            return _demo_sensors()
        try:
            return app.config["READER"].read_all_sensors()
        except Exception as exc:
            return {"error": {"value": None, "unit": None, "error": str(exc)}}

    def _get_status():
        if app.config["DEMO"]:
            return {"connected": True, "port": "DEMO", "mode": "demo"}
        conn = app.config["CONNECTOR"]
        if conn is None:
            return {"connected": False, "port": None, "mode": None}
        return {
            "connected": conn.is_connected(),
            "port": conn.port,
            "mode": type(conn).__name__,
        }

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.route("/")
    def index():
        return render_template("index.html", demo=app.config["DEMO"])

    @app.route("/api/status")
    def api_status():
        return jsonify(_get_status())

    @app.route("/api/sensors")
    def api_sensors():
        return jsonify({"sensors": _get_sensors()})

    @app.route("/api/dtc")
    def api_dtc():
        if app.config["DEMO"] or app.config["READER"] is None:
            return jsonify({"codes": []})
        try:
            codes = app.config["READER"].read_dtc()
            return jsonify({"codes": codes})
        except Exception as exc:
            return jsonify({"codes": [], "error": str(exc)})

    @app.route("/api/dtc/clear", methods=["POST"])
    def api_dtc_clear():
        if app.config["DEMO"] or app.config["WRITER"] is None:
            return jsonify({"success": True, "demo": True})
        try:
            success = app.config["WRITER"].clear_dtc()
            return jsonify({"success": success})
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)})

    @app.route("/api/command", methods=["POST"])
    def api_command():
        body = request.get_json(silent=True) or {}
        command = body.get("command", "").strip()
        if not command:
            return jsonify({"response": "", "error": "No command provided"}), 400
        if app.config["DEMO"] or app.config["WRITER"] is None:
            return jsonify({"response": f"DEMO> {command}\r\nOK"})
        try:
            response = app.config["WRITER"].send_raw(command)
            return jsonify({"response": response})
        except Exception as exc:
            return jsonify({"response": "", "error": str(exc)})

    @app.route("/api/export")
    def api_export():
        sensors = _get_sensors()
        timestamp = datetime.now().isoformat()
        lines = ["timestamp,sensor,value,unit,error"]
        for name, info in sensors.items():
            lines.append(f"{timestamp},{name},{info.get('value','')},{info.get('unit','')},{info.get('error','')}")
        csv_data = "\n".join(lines)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=obd2_data_{ts}.csv"},
        )

    @app.route("/api/stream")
    def api_stream():
        stream_interval = app.config.get("STREAM_INTERVAL", 2)  # seconds between SSE pushes

        @stream_with_context
        def generate():
            while True:
                sensors = _get_sensors()
                status  = _get_status()
                payload = json.dumps({"sensors": sensors, "status": status,
                                      "timestamp": datetime.now().isoformat()})
                yield f"data: {payload}\n\n"
                time.sleep(stream_interval)

        return Response(generate(), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache",
                                 "X-Accel-Buffering": "no"})

    return app
