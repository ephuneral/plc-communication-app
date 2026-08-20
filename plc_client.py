import snap7
from config import PlcConfig
import logging

log = logging.getLogger(__name__)

# Class Clent
class PlcClient:
    def __init__(self, cfg: PlcConfig):
        self.cfg = cfg
        self.client = snap7.client.Client()

    # Connect function with cfg configuration
    def connect(self) -> None:
        log.info(f"Config {self.cfg.ip}")
        self.client.connect(
            self.cfg.ip,
            0,
            1
        )
        log.info(f"Connected to PLC {self.cfg.ip}")

    # Dissconnect from PLC
    def close(self) -> None:
        try:
            self.client.disconnect()
        except Exception:
            pass

    # Reconnect to PLC
    def reconnect(self) -> None:
        self.close()
        self.client = snap7.client.Client()
        self.connect()
