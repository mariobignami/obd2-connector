"""Interactive CLI interface using Rich and Click."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box

console = Console()


class CLIInterface:
    """REPL-style command-line interface for the OBD2 connector."""

    HELP_TEXT = """
[bold cyan]Available commands:[/bold cyan]
  [green]scan[/green]           Read all sensor values
  [green]dtc[/green]            Read Diagnostic Trouble Codes
  [green]clear_dtc[/green]      Clear stored DTCs (Mode 04)
  [green]send <cmd>[/green]     Send a raw AT or OBD2 command
  [green]export[/green]         Export current sensor data to CSV
  [green]help[/green]           Show this help message
  [green]exit[/green]           Quit the interface
"""

    def __init__(self, connector, reader, writer):
        self.connector = connector
        self.reader = reader
        self.writer = writer
        self._last_scan: dict = {}

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------

    def run(self):
        """Start the interactive REPL loop."""
        console.print(Panel("[bold green]OBD2 Connector[/bold green] — Interactive CLI",
                            subtitle="Type [cyan]help[/cyan] for commands",
                            box=box.DOUBLE_EDGE))
        while True:
            try:
                raw_input = Prompt.ask("\n[bold yellow]obd2>[/bold yellow]").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Exiting…[/dim]")
                break

            if not raw_input:
                continue

            parts = raw_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd == "exit":
                console.print("[dim]Goodbye.[/dim]")
                break
            elif cmd == "help":
                console.print(self.HELP_TEXT)
            elif cmd == "scan":
                self._cmd_scan()
            elif cmd == "dtc":
                self._cmd_dtc()
            elif cmd == "clear_dtc":
                self._cmd_clear_dtc()
            elif cmd == "send":
                self._cmd_send(arg)
            elif cmd == "export":
                self._cmd_export()
            else:
                console.print(f"[red]Unknown command:[/red] {cmd}  (type [cyan]help[/cyan])")

    # ------------------------------------------------------------------
    # Command implementations
    # ------------------------------------------------------------------

    def _cmd_scan(self):
        console.print("[bold]Scanning all sensors…[/bold]")
        data = self.reader.read_all_sensors()
        self._last_scan = data
        self._render_sensor_table(data)

    def _cmd_dtc(self):
        console.print("[bold]Reading DTC codes…[/bold]")
        codes = self.reader.read_dtc()
        if codes:
            table = Table(title="Diagnostic Trouble Codes", box=box.SIMPLE_HEAD)
            table.add_column("Code", style="red bold")
            for code in codes:
                table.add_row(code)
            console.print(table)
        else:
            console.print("[green]No DTC codes found.[/green]")

    def _cmd_clear_dtc(self):
        confirm = Prompt.ask("[bold red]Clear all DTCs? This cannot be undone[/bold red]",
                             choices=["y", "n"], default="n")
        if confirm == "y":
            success = self.writer.clear_dtc()
            if success:
                console.print("[green]DTCs cleared successfully.[/green]")
            else:
                console.print("[red]Failed to clear DTCs.[/red]")
        else:
            console.print("[dim]Cancelled.[/dim]")

    def _cmd_send(self, command: str):
        if not command:
            console.print("[red]Usage:[/red] send <command>")
            return
        console.print(f"[dim]Sending:[/dim] {command}")
        response = self.writer.send_raw(command)
        console.print(Panel(response or "[dim](empty response)[/dim]",
                            title="Response", border_style="cyan"))

    def _cmd_export(self):
        from utils.export import CSVExporter
        if not self._last_scan:
            console.print("[yellow]No scan data yet — running scan first…[/yellow]")
            self._cmd_scan()
        filename = CSVExporter().export(self._last_scan)
        console.print(f"[green]Exported to:[/green] {filename}")

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _render_sensor_table(data: dict):
        table = Table(title="OBD2 Sensor Readings", box=box.ROUNDED,
                      show_header=True, header_style="bold magenta")
        table.add_column("Sensor", style="cyan", min_width=16)
        table.add_column("Value", justify="right", style="bold white")
        table.add_column("Unit", style="green")
        table.add_column("Status", style="dim")

        for name, info in data.items():
            value = info.get("value")
            unit  = info.get("unit", "")
            error = info.get("error")
            if error:
                table.add_row(name, "—", unit or "", f"[red]{error}[/red]")
            else:
                v_str = f"{value:.2f}" if isinstance(value, float) else str(value)
                table.add_row(name, v_str, unit, "[green]OK[/green]")

        console.print(table)
