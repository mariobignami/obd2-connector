import logging
import serial
import time
from .base import BaseConnector

logger = logging.getLogger(__name__)


class SerialConnector(BaseConnector):
    """Connector for USB/Serial OBD2 adapters (ELM327)."""

    def __init__(self, port: str, baudrate: int = 38400, timeout: int = 1):
        super().__init__(port, baudrate, timeout)

    def connect(self) -> bool:
        try:
            logger.info("[USB] Connecting to Serial OBD2 on port %s…", self.port)
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            time.sleep(2)
            if self.connection.is_open:
                logger.info("[USB] Connected successfully on %s", self.port)
                self.initialize()
                return True
            return False
        except serial.SerialException as e:
            logger.error("[USB][ERROR] Could not connect: %s", e)
            return False

    @staticmethod
    def list_serial_ports():
        """Lists all available serial/USB ports."""
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        available = [p.device for p in ports]
        if not available:
            logger.warning("[USB] No serial ports found.")
        return available
