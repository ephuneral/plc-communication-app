import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from db import PgWriter

app = FastAPI(title="PLC Pipes API")

pg_dsn = os.getenv("PG_DSN")
if not pg_dsn:
    raise ValueError("Переменная PG_DSN не найдена в файле .env!")

pg = PgWriter(pg_dsn)

@app.get("/pipes")
def search_pipes(
    page: int = 1,
    page_size: int = 20,
    serial_number: Optional[int] = None,
    factory_number: Optional[int] = None,
    diameter: Optional[int] = None,
    thickness: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
):
    result = pg.search(
        page=page, page_size=page_size,
        serial_number=serial_number, factory_number=factory_number,
        diameter=diameter, thickness=thickness,
        date_from=date_from, date_to=date_to,
    )

    items = [
        {
            "id": p.id,
            "ts": p.ts.isoformat() if p.ts else None,
            "length": p.length,
            "diameter": p.diameter,
            "thickness": p.thickness,
            "serial_number": p.serial_number,
            "factory_number": p.factory_number,
            "operator": p.operator,
            "pressure_start": p.pressure_start,
            "pressure_end": p.pressure_end,
            "pressure_target": p.pressure_target,
            "duration": p.duration,
            "result": p.result,
            "graph_x": p.graph_x,
            "graph_y": p.graph_y,
        }
        for p in result["items"]
    ]

    # ВАЖНО: возвращаем total и pages
    return {
        "items": items,
        "total": result.get("total", 0),
        "page": result.get("page", page),
        "page_size": result.get("page_size", page_size),
        "pages": result.get("pages", 1),
    }