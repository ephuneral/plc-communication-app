import logging
import os
import time
import snap7
from datetime import datetime
from db import Pipe, PgWriter
from config import load_config
from plc_client import PlcClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)
log = logging.getLogger(__name__)

def toggle_live_bit(plc: PlcClient, cfg):
    data = plc.client.db_read(cfg.recv_db_number, 0, 1)
    live_bit = snap7.util.get_bool(data, 0, 0)
    snap7.util.set_bool(data, 0, 0, not live_bit)
    plc.client.db_write(cfg.recv_db_number, 0, data)


def is_new_data_present(plc: PlcClient, cfg, data):
    if snap7.util.get_bool(data, 0, 0):
        snap7.util.set_bool(data, 0, 0, False)
        plc.client.db_write(cfg.send_db_number, 0, data)
        return True
    else:
        return False


def is_need_read(plc: PlcClient, cfg, data):
    if snap7.util.get_bool(data, 0, 1):
        snap7.util.set_bool(data, 0, 1, False)
        plc.client.db_write(cfg.send_db_number, 0, data)
        return True
    else:
        return False


def parse_datetime(data, offset=0) -> datetime | None:
    try:
        day = snap7.util.get_usint(data, 0 + offset)
        month = snap7.util.get_usint(data, 1 + offset)
        year = snap7.util.get_uint(data, 2 + offset)
        hour = snap7.util.get_usint(data, 4 + offset)
        minute = snap7.util.get_usint(data, 5 + offset)
        second = snap7.util.get_usint(data, 6 + offset)
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None


def parse_tube(plc: PlcClient, cfg) -> Pipe:
    raw = plc.client.db_read(cfg.send_db_number, 2, 404)
    return Pipe(
        ts=parse_datetime(raw),
        length=snap7.util.get_uint(raw, 8),
        diameter=snap7.util.get_uint(raw, 10),
        thickness=snap7.util.get_uint(raw, 12),
        serial_number=snap7.util.get_udint(raw, 14),
        factory_number=snap7.util.get_udint(raw, 18),
        operator=snap7.util.get_string(raw, 22),
        pressure_start=snap7.util.get_uint(raw, 34),
        pressure_end=snap7.util.get_uint(raw, 36),
        pressure_target=snap7.util.get_uint(raw, 38),
        duration=snap7.util.get_uint(raw, 40),
        result=snap7.util.get_uint(raw, 42),
        graph_x=[snap7.util.get_uint(raw, 44 + i*2) for i in range(90)],
        graph_y=[snap7.util.get_uint(raw, 224 + i*2) for i in range(90)]
    )


def map_tube(pipe, data):
    snap7.util.set_usint(data, 0, pipe.ts.day)
    snap7.util.set_usint(data, 1, pipe.ts.month)
    snap7.util.set_uint(data, 2, pipe.ts.year)
    snap7.util.set_usint(data, 4, pipe.ts.hour)
    snap7.util.set_usint(data, 5, pipe.ts.minute)
    snap7.util.set_usint(data, 6, pipe.ts.second)
    snap7.util.set_uint(data, 8, pipe.length)
    snap7.util.set_uint(data, 10, pipe.diameter)
    snap7.util.set_uint(data, 12, pipe.thickness)
    snap7.util.set_udint(data, 14, pipe.serial_number)
    snap7.util.set_udint(data, 18, pipe.factory_number)
    snap7.util.set_string(data, 22, pipe.operator, 10)
    snap7.util.set_uint(data, 34, pipe.pressure_start)
    snap7.util.set_uint(data, 36, pipe.pressure_end)
    snap7.util.set_uint(data, 38, pipe.pressure_target)
    snap7.util.set_uint(data, 40, pipe.duration)
    snap7.util.set_uint(data, 42, pipe.result)
    for i in range(90):
        snap7.util.set_uint(data, 44 + (i * 2), pipe.graph_x[i])
    for i in range(90):
        snap7.util.set_uint(data, 224 + (i * 2), pipe.graph_y[i])

    return data


def write_tubes_in_plc(plc: PlcClient, cfg, pipes):
    for i in range(10):
        data = plc.client.db_read(cfg.recv_db_number, 2 + (i * 404), 404)
        if i < len(pipes):
            data = map_tube(pipes[i], data)
            plc.client.db_write(cfg.recv_db_number, 2 + (i * 404), data)
        else:
            data = map_tube(
                Pipe(
                    ts=datetime(1970, 1, 1),
                    length=0,
                    diameter=0,
                    thickness=0,
                    serial_number=0,
                    factory_number=0,
                    operator='',
                    pressure_start=0,
                    pressure_end=0,
                    pressure_target=0,
                    duration=0,
                    result=0,
                    graph_x=[0 for _ in range(90)],
                    graph_y=[0 for _ in range(90)]
                ),
                data
            )
            plc.client.db_write(cfg.recv_db_number, 2 + (i * 404), data)


def main() -> None:
    cfg = load_config()

    pg_dsn = os.getenv("PG_DSN")
    if not pg_dsn:
        raise SystemExit("PG_DSN не задан в .env")

    pg = PgWriter(pg_dsn)
    log.info("PostgreSQL connected")

    plc = PlcClient(cfg)
    plc.connect()

    last_read = 0.0
    last_heartbeat = 0.0

    while True:
        now = time.time()

        try:
            if now - last_heartbeat >= 1:
                last_heartbeat = now
                toggle_live_bit(plc, cfg)

            if now - last_read >= cfg.poll_seconds:
                last_read = now
                data = plc.client.db_read(cfg.send_db_number, 0, 1)
                if is_new_data_present(plc, cfg, data):
                    pg.write(parse_tube(plc, cfg))
                elif is_need_read(plc, cfg, data):
                    params = plc.client.db_read(cfg.send_db_number, 406, 30)
                    result = pg.search(
                        page=snap7.util.get_uint(params, 0),
                        diameter=snap7.util.get_uint(params, 2),
                        thickness=snap7.util.get_uint(params, 4),
                        serial_number=snap7.util.get_udint(params, 6),
                        factory_number=snap7.util.get_udint(params, 10),
                        date_from=parse_datetime(params, 14),
                        date_to=parse_datetime(params, 22),
                        page_size=10
                    )
                    write_tubes_in_plc(plc, cfg, result['items'])


            time.sleep(cfg.poll_seconds)
        except Exception as e:
            log.error(e)
            break

    plc.close()


if __name__ == "__main__":
    main()
