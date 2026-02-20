import logging
import serial
import time
from .base import BaseConnector

logger = logging.getLogger(__name__)


class BluetoothConnector(BaseConnector):
    """Connector for Bluetooth OBD2 adapters (ELM327)."""

    def __init__(self, port: str, baudrate: int = 38400, timeout: int = 1):
        super().__init__(port, baudrate, timeout)

    def connect(self) -> bool:
        try:
            logger.info("[BT] Connecting to Bluetooth OBD2 on port %s…", self.port)
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            time.sleep(2)
            if self.connection.is_open:
                logger.info("[BT] Connected successfully on %s", self.port)
                self.initialize()
                return True
            return False
        except serial.SerialException as e:
            logger.error("[BT][ERROR] Could not connect: %s", e)
            return False

    @staticmethod
    def list_bluetooth_ports():
        """Lists likely Bluetooth COM/rfcomm ports."""
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        bt_ports = [p.device for p in ports if "bluetooth" in p.description.lower() or "rfcomm" in p.device.lower()]
        if not bt_ports:
            logger.warning("[BT] No Bluetooth ports detected automatically. Please specify manually.")
        return bt_ports
