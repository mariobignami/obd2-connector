import serial
import time
from .base import BaseConnector


class SerialConnector(BaseConnector):
    """Connector for USB/Serial OBD2 adapters (ELM327)."""

    def __init__(self, port: str, baudrate: int = 38400, timeout: int = 1):
        super().__init__(port, baudrate, timeout)

    def connect(self) -> bool:
        try:
            print(f"[USB] Connecting to Serial OBD2 on port {self.port}...")
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            time.sleep(2)
            if self.connection.isOpen():
                print(f"[USB] Connected successfully on {self.port}")
                self.initialize()
                return True
            return False
        except serial.SerialException as e:
            print(f"[USB][ERROR] Could not connect: {e}")
            return False

    @staticmethod
    def list_serial_ports():
        """Lists all available serial/USB ports."""
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        available = [p.device for p in ports]
        if not available:
            print("[USB] No serial ports found.")
        else:
            print("[USB] Available ports:")
            for p in available:
                print(f"  - {p}")
        return available
