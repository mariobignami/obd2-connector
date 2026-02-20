"""
OBD2 writer – send raw AT and OBD2 commands to the vehicle.
"""

from .commands import AT_COMMANDS


class OBDWriter:
    """Sends commands to the vehicle through a BaseConnector."""

    def __init__(self, connector):
        self.connector = connector

    # ------------------------------------------------------------------
    # Raw command
    # ------------------------------------------------------------------

    def send_raw(self, command: str) -> str:
        """
        Send any raw AT or OBD2 command string.

        Returns the raw response string from the ELM327.
        """
        return self.connector.send_command(command)

    # ------------------------------------------------------------------
    # Named AT commands
    # ------------------------------------------------------------------

    def send_at(self, name: str) -> str:
        """
        Send a named AT command from the AT_COMMANDS dict.

        Example: writer.send_at("ECHO_OFF")
        """
        if name not in AT_COMMANDS:
            raise ValueError(
                f"Unknown AT command name: '{name}'. "
                f"Available: {list(AT_COMMANDS)}"
            )
        return self.send_raw(AT_COMMANDS[name])

    # ------------------------------------------------------------------
    # Protocol control
    # ------------------------------------------------------------------

    def set_protocol(self, protocol_number: int) -> str:
        """
        Set the OBD protocol explicitly.

        protocol_number:
          0  = Auto
          1  = SAE J1850 PWM
          2  = SAE J1850 VPW
          3  = ISO 9141-2
          4  = ISO 14230-4 KWP (5 baud init)
          5  = ISO 14230-4 KWP (fast init)
          6  = ISO 15765-4 CAN (11 bit, 500 kbaud)
          7  = ISO 15765-4 CAN (29 bit, 500 kbaud)
          8  = ISO 15765-4 CAN (11 bit, 250 kbaud)
          9  = ISO 15765-4 CAN (29 bit, 250 kbaud)
          A  = SAE J1939 CAN
        """
        return self.send_raw(f"AT SP {protocol_number:X}")

    # ------------------------------------------------------------------
    # Reset / init
    # ------------------------------------------------------------------

    def reset(self) -> str:
        """Perform a full ELM327 reset (AT Z)."""
        return self.send_at("RESET")

    def soft_reset(self) -> str:
        """Warm-start the ELM327 without forgetting protocol (AT WS)."""
        return self.send_raw("AT WS")

    # ------------------------------------------------------------------
    # CAN / headers
    # ------------------------------------------------------------------

    def set_header(self, header: str) -> str:
        """
        Set a custom CAN/OBD header (AT SH <header>).
        Example: writer.set_header("7DF")
        """
        return self.send_raw(f"AT SH {header.upper()}")

    def set_can_id_filter(self, mask: str) -> str:
        """
        Set a CAN receive filter (AT CF <mask>).
        """
        return self.send_raw(f"AT CF {mask.upper()}")

    def set_can_mask(self, mask: str) -> str:
        """
        Set a CAN receive mask (AT CM <mask>).
        """
        return self.send_raw(f"AT CM {mask.upper()}")

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------

    def set_timeout(self, value: int) -> str:
        """
        Set the ELM327 response timeout (AT ST <hex>).
        Value is in multiples of 4 ms; range 0x00–0xFF.
        """
        return self.send_raw(f"AT ST {value:02X}")
