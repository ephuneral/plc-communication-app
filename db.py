from datetime import datetime

from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.exc import SQLAlchemyError

from sqlalchemy import (
    BigInteger,
    REAL,
    DateTime,
    Index,
    Integer,
    String,
    func,
    create_engine,
    select,
    func,
    and_
)

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
)


class Base(DeclarativeBase):
    pass


# Pipe Entity
class Pipe(Base):
    __tablename__ = "pipes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
    )

    length: Mapped[int] = mapped_column(Integer)
    diameter: Mapped[int] = mapped_column(REAL)
    thickness: Mapped[int] = mapped_column(REAL)

    serial_number: Mapped[int] = mapped_column(BigInteger)
    factory_number: Mapped[int] = mapped_column(BigInteger)

    operator: Mapped[str] = mapped_column(String(10))

    pressure_start: Mapped[int] = mapped_column(REAL)
    pressure_end: Mapped[int] = mapped_column(REAL)
    pressure_target: Mapped[int] = mapped_column(Integer)

    duration: Mapped[int] = mapped_column(Integer)
    result: Mapped[int] = mapped_column(Integer)

    graph_x: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    graph_y: Mapped[list[int]] = mapped_column(ARRAY(Integer))

    __table_args__ = (
        Index("ix_serial_number", "serial_number"),
        Index("ix_factory_number", "factory_number"),
        Index("ix_diameter", "diameter"),
        Index("ix_thickness", "thickness"),
        Index("ix_ts", "ts"),
    )


# Database class
class PgWriter:
    def __init__(self, dsn: str):
        self.engine = create_engine(
            dsn,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        Base.metadata.create_all(self.engine)

    # Method for search with parameters
    def search(self, page=1, page_size=20, serial_number=None, factory_number=None,
               diameter=None, thickness=None, date_from=None, date_to=None):
        conditions = []

        if serial_number is not None and serial_number != 0:
            conditions.append(Pipe.serial_number == serial_number)
        if factory_number is not None and factory_number != 0:
            conditions.append(Pipe.factory_number == factory_number)
        if diameter is not None and diameter != 0:
            conditions.append(Pipe.diameter == diameter)
        if thickness is not None and thickness != 0:
            conditions.append(Pipe.thickness == thickness)
        if date_from is not None:
            conditions.append(Pipe.ts >= date_from)
        if date_to is not None:
            conditions.append(Pipe.ts <= date_to)

        with Session(self.engine) as session:
            stmt = select(Pipe)
            count_stmt = select(func.count()).select_from(Pipe)

            if conditions:
                stmt = stmt.where(and_(*conditions))
                count_stmt = count_stmt.where(and_(*conditions))

            total = session.execute(count_stmt).scalar() or 0

            offset = (page - 1) * page_size
            stmt = (
                stmt
                .order_by(Pipe.ts.desc())
                .limit(page_size)
                .offset(offset)
            )

            items = session.execute(stmt).scalars().all()

            pages = max(1, (total + page_size - 1) // page_size) if page_size > 0 else 1

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": pages,
            }

    # Method to write one pipe in database
    def write(self, data: Pipe) -> None:
        with Session(self.engine) as session:
            try:
                session.add(data)
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise
