from dataclasses import dataclass
import os
from dotenv import load_dotenv

@dataclass(frozen=True)
class PlcConfig:
    ip: str
    db_number: int
    poll_seconds: float


def load_config() -> PlcConfig:
    load_dotenv()

    return PlcConfig(
        ip=os.getenv("PLC_IP", "192.168.0.1"),
        db_number=int(os.getenv("PLC_DB", 100)),
        poll_seconds=float(os.getenv("POLL_SECONDS", 0.5))
    )