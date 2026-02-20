#!/usr/bin/env python3
"""OBD2 Connector — entry point."""

import sys
import click


@click.command()
@click.option("--mode", type=click.Choice(["bluetooth", "serial"]),
              default="serial", show_default=True,
              help="Connection mode")
@click.option("--port", default=None, help="Serial/Bluetooth port (e.g. /dev/rfcomm0 or COM3)")
@click.option("--baudrate", default=38400, show_default=True, help="Baud rate")
@click.option("--web",  is_flag=True, default=False, help="Start the web dashboard")
@click.option("--web-port", default=5000, show_default=True, help="Web server port")
@click.option("--demo", is_flag=True, default=False, help="Run in demo mode (no hardware needed)")
@click.option("--interactive", is_flag=True, default=False, help="Start interactive CLI")
def main(mode, port, baudrate, web, web_port, demo, interactive):
    """OBD2 Connector — read sensor data from an ELM327 OBD2 adapter."""

    connector = None
    reader    = None
    writer    = None

    if not demo:
        if port is None:
            click.echo("[ERROR] --port is required when not in --demo mode.", err=True)
            sys.exit(1)

        if mode == "bluetooth":
            from connector.bluetooth import BluetoothConnector
            connector = BluetoothConnector(port=port, baudrate=baudrate)
        else:
            from connector.serial_conn import SerialConnector
            connector = SerialConnector(port=port, baudrate=baudrate)

        connected = connector.connect()
        if not connected:
            click.echo("[ERROR] Failed to connect. Check port and device.", err=True)
            sys.exit(1)

        from obd.reader import OBD2Reader
        from obd.writer import OBD2Writer
        reader = OBD2Reader(connector)
        writer = OBD2Writer(connector)

    # ── Web dashboard ────────────────────────────────────────────────────
    if web:
        from web.app import create_app
        app = create_app(connector=connector, reader=reader, writer=writer, demo=demo)
        click.echo(f"[OBD2] Starting web dashboard on http://localhost:{web_port}")
        if demo:
            click.echo("[OBD2] Running in DEMO MODE — no hardware required.")
        app.run(host="0.0.0.0", port=web_port, threaded=True)
        return

    # ── Interactive CLI ──────────────────────────────────────────────────
    if interactive:
        if demo:
            click.echo("[WARN] --interactive requires a real connection; --demo ignored.", err=True)
            sys.exit(1)
        from cli.interface import CLIInterface
        cli = CLIInterface(connector=connector, reader=reader, writer=writer)
        cli.run()
        return

    # ── One-shot scan ────────────────────────────────────────────────────
    if demo:
        click.echo("[OBD2] Demo mode: use --web or --interactive with a real device.")
        sys.exit(0)

    click.echo("[OBD2] Running one-shot sensor scan…")
    data = reader.read_all_sensors()
    click.echo(f"{'Sensor':<18} {'Value':>10}  Unit")
    click.echo("-" * 36)
    for name, info in data.items():
        v = info.get("value")
        v_str = f"{v:.2f}" if isinstance(v, float) else str(v)
        unit  = info.get("unit", "")
        err   = info.get("error")
        if err:
            click.echo(f"{name:<18} {'ERROR':>10}  {err}")
        else:
            click.echo(f"{name:<18} {v_str:>10}  {unit}")

    if connector:
        connector.disconnect()


if __name__ == "__main__":
    main()
