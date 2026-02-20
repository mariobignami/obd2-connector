import serial
import time
from abc import ABC, abstractmethod


class BaseConnector(ABC):
    """Base class for OBD2 connectors."""

    def __init__(self, port: str, baudrate: int = 38400, timeout: int = 1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None

    @abstractmethod
    def connect(self) -> bool:
        pass

    def disconnect(self):
        if self.connection and self.connection.isOpen():
            self.connection.close()

    def is_connected(self) -> bool:
        return self.connection is not None and self.connection.isOpen()

    def send_command(self, command: str) -> str:
        if not self.is_connected():
            raise ConnectionError("Not connected to OBD2 device.")
        self.connection.write((command.strip() + "\r").encode())
        time.sleep(0.3)
        response = b""
        while self.connection.in_waiting:
            response += self.connection.read(self.connection.in_waiting)
            time.sleep(0.1)
        return response.decode(errors="ignore").strip()

    def reset(self) -> str:
        return self.send_command("AT Z")

    def set_auto_protocol(self) -> str:
        return self.send_command("AT SP 0")

    def echo_off(self) -> str:
        return self.send_command("AT E0")

    def linefeeds_off(self) -> str:
        return self.send_command("AT L0")

    def initialize(self) -> bool:
        try:
            self.reset()
            time.sleep(1)
            self.echo_off()
            self.linefeeds_off()
            self.set_auto_protocol()
            return True
        except Exception as e:
            print(f"[ERROR] Initialization failed: {e}")
            return False
