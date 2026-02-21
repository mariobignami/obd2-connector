"""
Rich-powered terminal interface for the OBD2 connector.

Provides:
  - Live real-time sensor dashboard
  - Interactive REPL with tab-completion
  - DTC viewer / clearer
  - Freeze-frame reader
  - Vehicle info (VIN, ECU name, …)
  - Data export (CSV / JSON)
  - Trip computer (speed, distance, avg speed)
  - Threshold alerts
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.columns import Columns
from rich.text import Text
from rich import box
from rich.prompt import Prompt, Confirm

from obd.commands import OBD_PIDS, DTC_PREFIXES
from obd.reader import OBDReader
from obd.writer import OBDWriter
from utils.export import export_csv, export_csv_log, export_json

console = Console()

# ---------------------------------------------------------------------------
# DTC display maps (module-level for reuse)
# ---------------------------------------------------------------------------

DTC_SYSTEM_MAP = {"P": "Powertrain", "C": "Chassis", "B": "Body", "U": "Network (CAN)"}
DTC_SUBTYPE_MAP = {"0": "Generic", "2": "Generic", "1": "Manufacturer", "3": "Manufacturer"}

# ---------------------------------------------------------------------------
# Colour thresholds
# ---------------------------------------------------------------------------

def _value_style(key: str, value: Any) -> str:
    """Return a Rich style string based on value vs alert thresholds."""
    if value is None:
        return "dim"
    info = OBD_PIDS.get(key, {})
    alert_high = info.get("alert_high")
    alert_low = info.get("alert_low")
    if alert_high is not None and value >= alert_high:
        return "bold red"
    if alert_low is not None and value <= alert_low:
        return "bold yellow"
    return "bold green"


# ---------------------------------------------------------------------------
# CLIInterface
# ---------------------------------------------------------------------------

class CLIInterface:
    """Main CLI façade – wires connector → reader/writer → rich UI."""

    def __init__(self, connector):
        self.connector = connector
        self.reader = OBDReader(connector)
        self.writer = OBDWriter(connector)

        self._session_log: List[Dict[str, Any]] = []
        self._latest_snapshot: Dict[str, Any] = {}
        self._log_lock = threading.Lock()

        # Trip computer state
        self._trip_start: Optional[float] = None
        self._prev_speed: float = 0.0
        self._prev_sample_time: Optional[float] = None
        self._trip_distance_km: float = 0.0
        self._speed_samples: List[float] = []

    # ------------------------------------------------------------------
    # Real-time dashboard
    # ------------------------------------------------------------------

    def run_dashboard(self, interval: float = 1.0, log_csv: bool = False) -> None:
        """
        Display a live-updating dashboard with all sensor values.
        Press Ctrl+C to stop.
        """
        self._trip_start = time.time()

        log_path: Optional[str] = None
        if log_csv:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = f"obd2_session_{ts}.csv"
            console.print(f"[dim]Logging to {log_path}[/]")

        def _on_snapshot(snapshot: Dict[str, Any]):
            with self._log_lock:
                self._latest_snapshot = snapshot
                self._session_log.append(snapshot)
            self._update_trip(snapshot)
            if log_csv and log_path:
                export_csv(snapshot, path=log_path, append=True)

        self.reader.start_realtime(_on_snapshot, interval=interval)

        try:
            with Live(self._build_dashboard(), refresh_per_second=2, console=console) as live:
                while True:
                    time.sleep(0.5)
                    live.update(self._build_dashboard())
        except KeyboardInterrupt:
            pass
        finally:
            self.reader.stop_realtime()
            if log_csv and log_path and self._session_log:
                console.print(f"\n[green]Session log saved → {log_path}[/]")

    def _build_dashboard(self) -> Table:
        snap = self._latest_snapshot
        ts = snap.get("_timestamp")
        ts_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "–"

        # Main sensor table
        tbl = Table(
            title=f"🚗 OBD2 Live Dashboard  [{ts_str}]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        tbl.add_column("Sensor", style="cyan", no_wrap=True)
        tbl.add_column("Value", justify="right")
        tbl.add_column("Unit", style="dim", no_wrap=True)
        tbl.add_column("Status", no_wrap=True)

        for key, info in OBD_PIDS.items():
            if key == "MIL_STATUS":
                continue
            val = snap.get(key)
            style = _value_style(key, val)
            val_str = f"{val}" if val is not None else "–"
            unit_str = info.get("unit", "")

            # Alert badge
            if style == "bold red":
                status = "⚠ HIGH"
            elif style == "bold yellow":
                status = "⚠ LOW"
            elif val is not None:
                status = "✓"
            else:
                status = "N/A"

            tbl.add_row(
                info["desc"],
                Text(val_str, style=style),
                unit_str,
                Text(status, style=style),
            )

        # Trip computer sub-panel
        trip_info = self._trip_summary()
        trip_tbl = Table(box=box.SIMPLE, show_header=False, expand=True)
        trip_tbl.add_column("Key", style="bold yellow")
        trip_tbl.add_column("Value", justify="right")
        for k, v in trip_info.items():
            trip_tbl.add_row(k, str(v))

        return Columns([tbl, Panel(trip_tbl, title="🗺 Trip Computer", border_style="yellow")])

    # ------------------------------------------------------------------
    # Trip computer
    # ------------------------------------------------------------------

    def _update_trip(self, snapshot: Dict[str, Any]) -> None:
        speed = snapshot.get("SPEED")
        now = snapshot.get("_timestamp") or time.time()
        if speed is not None:
            self._speed_samples.append(speed)
            if self._prev_sample_time is not None:
                dt = now - self._prev_sample_time
                avg = (self._prev_speed + speed) / 2
                self._trip_distance_km += avg / 3600 * dt
            self._prev_speed = speed
        self._prev_sample_time = now

    def _trip_summary(self) -> Dict[str, str]:
        elapsed = time.time() - (self._trip_start or time.time())
        avg_speed = (sum(self._speed_samples) / len(self._speed_samples)) if self._speed_samples else 0
        return {
            "Elapsed":        str(timedelta(seconds=int(elapsed))),
            "Distance":       f"{self._trip_distance_km:.2f} km",
            "Avg Speed":      f"{avg_speed:.1f} km/h",
            "Max Speed":      f"{max(self._speed_samples, default=0):.0f} km/h",
            "Samples":        str(len(self._speed_samples)),
        }

    # ------------------------------------------------------------------
    # Single scan (non-live)
    # ------------------------------------------------------------------

    def scan_all(self) -> None:
        """Read all PIDs once and print a formatted table."""
        console.print("[bold cyan]Scanning all sensors…[/]")
        data = self.reader.read_all()
        tbl = Table(title="OBD2 Sensor Scan", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        tbl.add_column("Key", style="cyan")
        tbl.add_column("Sensor")
        tbl.add_column("Value", justify="right")
        tbl.add_column("Unit", style="dim")

        for key, info in OBD_PIDS.items():
            if key == "MIL_STATUS":
                continue
            val = data.get(key)
            val_str = f"{val}" if val is not None else "–"
            style = _value_style(key, val)
            tbl.add_row(key, info["desc"], Text(val_str, style=style), info.get("unit", ""))

        console.print(tbl)

    # ------------------------------------------------------------------
    # DTC commands
    # ------------------------------------------------------------------

    def show_dtcs(self, pending: bool = False) -> None:
        if pending:
            dtcs = self.reader.read_pending_dtcs()
            title = "Pending DTCs (Mode 07)"
        else:
            dtcs = self.reader.read_dtcs()
            title = "Stored DTCs (Mode 03)"

        if not dtcs:
            console.print(f"[green]✓ No {title} found.[/]")
            return

        _system_map = DTC_SYSTEM_MAP
        _subtype_map = DTC_SUBTYPE_MAP

        tbl = Table(title=title, box=box.ROUNDED, header_style="bold red")
        tbl.add_column("Code", style="bold red")
        tbl.add_column("System")
        tbl.add_column("Type")
        for dtc in dtcs:
            system = _system_map.get(dtc[0], "Unknown") if dtc else "Unknown"
            subtype = _subtype_map.get(dtc[1], "") if len(dtc) > 1 else ""
            tbl.add_row(dtc, system, subtype)
        console.print(tbl)

    def clear_dtcs(self) -> None:
        if Confirm.ask("[bold red]Clear all stored DTCs? This cannot be undone.[/]"):
            resp = self.reader.clear_dtcs()
            console.print(f"[green]Response:[/] {resp}")
        else:
            console.print("[dim]Aborted.[/]")

    # ------------------------------------------------------------------
    # Vehicle info
    # ------------------------------------------------------------------

    def show_vehicle_info(self) -> None:
        with console.status("[cyan]Reading vehicle information…[/]"):
            vin = self.reader.read_vin()
            ecu = self.reader.read_ecu_name()
            cal = self.reader.read_calibration_id()
            proto = self.reader.get_protocol()
            elm = self.reader.get_elm_version()
            bat = self.reader.get_battery_voltage()

        tbl = Table(title="Vehicle Information", box=box.ROUNDED, header_style="bold yellow")
        tbl.add_column("Field", style="bold yellow")
        tbl.add_column("Value")
        tbl.add_row("VIN", vin)
        tbl.add_row("ECU Name", ecu)
        tbl.add_row("Calibration ID", cal)
        tbl.add_row("OBD Protocol", proto)
        tbl.add_row("ELM327 Version", elm)
        tbl.add_row("Battery Voltage", bat)
        console.print(tbl)

    # ------------------------------------------------------------------
    # MIL (check engine light) status
    # ------------------------------------------------------------------

    def show_mil_status(self) -> None:
        with console.status("[cyan]Reading MIL status…[/]"):
            status = self.reader.read_mil_status()

        mil_on = status.get("mil_on")
        dtc_count = status.get("dtc_count")

        if mil_on is None:
            console.print("[red]Could not read MIL status.[/]")
            return

        if mil_on:
            console.print(f"[bold red]⚠  Check Engine Light is ON  ({dtc_count} DTC(s) stored)[/]")
        else:
            console.print(f"[bold green]✓  Check Engine Light is OFF  ({dtc_count} DTC(s) stored)[/]")

    # ------------------------------------------------------------------
    # Freeze frame
    # ------------------------------------------------------------------

    def show_freeze_frame(self, frame: int = 0) -> None:
        console.print(f"[cyan]Reading freeze frame {frame}…[/]")
        tbl = Table(title=f"Freeze Frame #{frame}", box=box.ROUNDED, header_style="bold cyan")
        tbl.add_column("Sensor")
        tbl.add_column("Value", justify="right")
        tbl.add_column("Unit", style="dim")

        for key, info in OBD_PIDS.items():
            if key == "MIL_STATUS":
                continue
            val = self.reader.read_freeze_frame(key, frame=frame)
            val_str = f"{val}" if val is not None else "–"
            tbl.add_row(info["desc"], val_str, info.get("unit", ""))

        console.print(tbl)

    # ------------------------------------------------------------------
    # Raw command
    # ------------------------------------------------------------------

    def send_command(self, cmd: str) -> None:
        resp = self.writer.send_raw(cmd)
        console.print(Panel(resp or "(no response)", title=f"Response to: {cmd}", border_style="dim"))

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_data(self, fmt: str = "csv") -> None:
        with self._log_lock:
            log = list(self._session_log)

        if not log:
            # Fallback: take a fresh single scan
            log = [self.reader.read_all()]
            log[0]["_timestamp"] = time.time()

        try:
            if fmt == "json":
                path = export_json(log)
            else:
                path = export_csv_log(log)
            console.print(f"[green]✓ Data exported → {path}[/]")
        except Exception as exc:
            console.print(f"[red]Export failed: {exc}[/]")

    # ------------------------------------------------------------------
    # Interactive REPL
    # ------------------------------------------------------------------

    def run_interactive(self) -> None:
        """Start the interactive command prompt."""
        self._print_banner()
        console.print("[dim]Type [bold]help[/bold] for a list of commands.[/dim]\n")

        while True:
            try:
                raw = Prompt.ask("[bold cyan]obd2>[/]").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[yellow]Exiting.[/]")
                break

            if not raw:
                continue

            parts = raw.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in ("exit", "quit", "q"):
                console.print("[yellow]Goodbye 👋[/]")
                break
            elif cmd == "help":
                self._print_help()
            elif cmd == "scan":
                self.scan_all()
            elif cmd == "dash":
                log_flag = "--log" in arg
                interval = 1.0
                for tok in arg.split():
                    try:
                        interval = float(tok)
                    except ValueError:
                        pass
                self.run_dashboard(interval=interval, log_csv=log_flag)
            elif cmd == "dtc":
                self.show_dtcs(pending=False)
            elif cmd == "pending":
                self.show_dtcs(pending=True)
            elif cmd == "clear_dtc":
                self.clear_dtcs()
            elif cmd == "freeze":
                frame = int(arg) if arg.isdigit() else 0
                self.show_freeze_frame(frame)
            elif cmd == "info":
                self.show_vehicle_info()
            elif cmd == "mil":
                self.show_mil_status()
            elif cmd == "trip":
                info = self._trip_summary()
                for k, v in info.items():
                    console.print(f"  [yellow]{k}:[/] {v}")
            elif cmd == "send":
                if arg:
                    self.send_command(arg)
                else:
                    console.print("[red]Usage: send <AT or OBD2 command>[/]")
            elif cmd == "export":
                fmt = arg.strip().lower() or "csv"
                self.export_data(fmt)
            elif cmd == "log":
                interval = float(arg) if arg else 1.0
                self.run_dashboard(interval=interval, log_csv=True)
            else:
                console.print(f"[red]Unknown command: '{cmd}'. Type 'help' for help.[/]")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _print_banner(self) -> None:
        console.print(Panel(
            "[bold cyan]OBD2 Connector[/bold cyan]  "
            "[dim]– Python ELM327 diagnostic tool[/dim]",
            border_style="cyan",
        ))

    def _print_help(self) -> None:
        tbl = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        tbl.add_column("Command", style="bold cyan", no_wrap=True)
        tbl.add_column("Description")
        commands = [
            ("scan",              "Read all sensors once and display a table"),
            ("dash [interval] [--log]",
                                  "Live-updating sensor dashboard (default 1 s interval; --log saves CSV)"),
            ("dtc",               "Show stored DTCs (Mode 03)"),
            ("pending",           "Show pending DTCs (Mode 07)"),
            ("clear_dtc",         "Clear stored DTCs (Mode 04) – asks for confirmation"),
            ("mil",               "Show MIL (check engine light) status and DTC count"),
            ("freeze [frame#]",   "Read freeze-frame data (default frame 0)"),
            ("info",              "Display vehicle info: VIN, ECU name, protocol, battery…"),
            ("trip",              "Show trip computer summary"),
            ("send <cmd>",        "Send a raw AT or OBD2 command and show the response"),
            ("export [csv|json]", "Export session data to CSV (default) or JSON"),
            ("log [interval]",    "Like 'dash' but always logs to CSV"),
            ("help",              "Show this help"),
            ("exit",              "Disconnect and quit"),
        ]
        for c, d in commands:
            tbl.add_row(c, d)
        console.print(tbl)
