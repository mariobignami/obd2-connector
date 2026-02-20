"""OBD2Writer — low-level command sending and DTC clearing."""

from .commands import AT_COMMANDS


class OBD2Writer:
    """Send raw commands and perform write operations via a BaseConnector."""

    def __init__(self, connector):
        self.connector = connector

    def send_raw(self, command: str) -> str:
        """Send any raw AT or OBD2 command and return the response string."""
        try:
            return self.connector.send_command(command)
        except Exception as exc:
            return f"ERROR: {exc}"

    def clear_dtc(self) -> bool:
        """Send Mode 04 to clear stored DTCs.

        Returns ``True`` if the adapter confirms with a ``"44"`` in the response.
        """
        try:
            response = self.connector.send_command("04")
            return "44" in response.upper()
        except Exception:
            return False

    def send_at(self, command: str) -> str:
        """Send an AT command (will prepend ``"AT "`` if not already present)."""
        cmd = command.strip()
        if not cmd.upper().startswith("AT"):
            cmd = "AT " + cmd
        return self.send_raw(cmd)

    def set_protocol(self, protocol: int) -> str:
        """Send ``AT SP {protocol}`` to select a specific OBD2 protocol."""
        return self.send_raw(f"AT SP {protocol}")

    def initialize(self) -> bool:
        """Run the standard ELM327 initialization sequence."""
        try:
            self.send_raw(AT_COMMANDS["reset"])
            import time; time.sleep(1)
            self.send_raw(AT_COMMANDS["echo_off"])
            self.send_raw(AT_COMMANDS["linefeeds_off"])
            self.send_raw(AT_COMMANDS["headers_off"])
            self.send_raw(AT_COMMANDS["auto_protocol"])
            return True
        except Exception:
            return False
