#!/usr/bin/env python3
"""
main.py – OBD2 Connector entry point.

Usage examples:
  python main.py --mode bluetooth --port /dev/rfcomm0
  python main.py --mode serial    --port /dev/ttyUSB0
  python main.py --mode serial    --port COM4  --interactive
  python main.py --mode bluetooth --port COM3  --dash --interval 0.5 --log
  python main.py list-ports
"""

import sys
import time

import click
from rich.console import Console

from connector import BluetoothConnector, SerialConnector
from cli.interface import CLIInterface

console = Console()


# ---------------------------------------------------------------------------
# Shared connection factory
# ---------------------------------------------------------------------------

def _build_connector(mode: str, port: str, baudrate: int, timeout: int):
    if mode == "bluetooth":
        return BluetoothConnector(port=port, baudrate=baudrate, timeout=timeout)
    if mode == "serial":
        return SerialConnector(port=port, baudrate=baudrate, timeout=timeout)
    console.print(f"[red]Unknown mode '{mode}'. Use 'bluetooth' or 'serial'.[/]")
    sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.group(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--mode",      "-m", default="serial",   show_default=True,
              type=click.Choice(["bluetooth", "serial"], case_sensitive=False),
              help="Connection mode.")
@click.option("--port",      "-p", default=None,       help="Serial/COM port (e.g. /dev/ttyUSB0, COM3).")
@click.option("--baudrate",  "-b", default=38400,       show_default=True, help="Baud rate.")
@click.option("--timeout",   "-t", default=1,           show_default=True, help="Serial timeout (seconds).")
@click.option("--interactive", "-i", is_flag=True,      help="Start interactive REPL after connecting.")
@click.option("--dash",          is_flag=True,          help="Launch live dashboard immediately.")
@click.option("--interval",  default=1.0, show_default=True, help="Dashboard refresh interval (seconds).")
@click.option("--log",           is_flag=True,          help="Log dashboard data to CSV automatically.")
@click.option("--scan",          is_flag=True,          help="Run a single sensor scan and exit.")
@click.option("--info",          is_flag=True,          help="Show vehicle info (VIN, ECU, …) and exit.")
@click.option("--dtc",           is_flag=True,          help="Show stored DTCs and exit.")
@click.pass_context
def cli(ctx, mode, port, baudrate, timeout, interactive, dash, interval, log, scan, info, dtc):
    """🚗 OBD2 Connector – Python ELM327 diagnostic tool."""

    # If a sub-command is being invoked (e.g. list-ports) skip the rest
    if ctx.invoked_subcommand is not None:
        return

    if port is None:
        console.print("[red]Error: --port is required. Use 'list-ports' to discover available ports.[/]")
        console.print("  Example: python main.py --mode serial --port /dev/ttyUSB0")
        sys.exit(1)

    connector = _build_connector(mode, port, baudrate, timeout)

    console.print(f"[cyan]Connecting via [bold]{mode}[/bold] on [bold]{port}[/bold]…[/]")
    if not connector.connect():
        console.print("[red]Failed to connect. Check the port and adapter.[/]")
        sys.exit(1)

    try:
        cli_iface = CLIInterface(connector)

        if info:
            cli_iface.show_vehicle_info()
        elif dtc:
            cli_iface.show_dtcs()
        elif scan:
            cli_iface.scan_all()
        elif dash:
            cli_iface.run_dashboard(interval=interval, log_csv=log)
        elif interactive:
            cli_iface.run_interactive()
        else:
            # Default: run interactive
            cli_iface.run_interactive()

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/]")
    finally:
        connector.disconnect()
        console.print("[dim]Connection closed.[/]")


@cli.command("list-ports")
def list_ports():
    """List all available serial/USB and detected Bluetooth ports."""
    from connector.serial_conn import SerialConnector
    from connector.bluetooth import BluetoothConnector
    console.print("[bold]Available serial ports:[/]")
    ports = SerialConnector.list_serial_ports()
    if not ports:
        console.print("  [dim](none found)[/]")
    console.print("\n[bold]Likely Bluetooth ports:[/]")
    bt = BluetoothConnector.list_bluetooth_ports()
    if not bt:
        console.print("  [dim](none detected automatically)[/]")


if __name__ == "__main__":
    cli()
