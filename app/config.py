from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Config class
@dataclass(frozen=True)
class PlcConfig:
    ip: str                 # IP address
    send_db_number: int     # Data Block SEND number
    recv_db_number: int     # Data block RECV number
    poll_seconds: float     # Sleep time between polls

# Load config from ,env to PlcConfig class
def load_config() -> PlcConfig:
    load_dotenv()

    return PlcConfig(
        ip=os.getenv("PLC_IP", "192.168.0.1"),
        send_db_number=int(os.getenv("PLC_SEND_DB", 100)),
        recv_db_number=int(os.getenv("PLC_RECV_DB", 101)),
        poll_seconds=float(os.getenv("POLL_SECONDS", 0.5))
    )