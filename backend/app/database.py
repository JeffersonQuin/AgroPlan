"""Engine y sesiones de la aplicación.

Desarrollo y demo corren sobre SQLite; producción puede apuntar a PostgreSQL con la
misma variable ``DATABASE_URL``. Para SQLite se configura el modo WAL: la corrida del
agente escribe en una tarea de fondo mientras el front hace polling, y con el journal
por defecto esa lectura choca contra el escritor ("database is locked" en plena demo).
WAL deja leer durante la escritura y ``busy_timeout`` hace esperar al segundo escritor
en vez de fallar.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


ES_SQLITE = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    future=True,
    connect_args={"timeout": 30} if ES_SQLITE else {},
)

if ES_SQLITE:

    @event.listens_for(engine, "connect")
    def _configurar_sqlite(conexion, _registro):  # pragma: no cover - hook del driver
        cursor = conexion.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
