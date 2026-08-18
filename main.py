import logging
import os
import time

from config import load_config
from plc_client import PlcClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)
log = logging.getLogger(__name__)

def main() -> None:
    cfg = load_config()

    plc = PlcClient(cfg)
    plc.connect()

    log.info(f"Reading DB{cfg.db_number}")

    while True:
        try:
            log.info(f"DB: {plc.client.db_read(cfg.db_number, 0, 1)}")

            time.sleep(cfg.poll_seconds)
        except Exception as e:
            log.error(e)
            break

    plc.close()


if __name__ == "__main__":
    main()


