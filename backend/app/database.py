import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# .as_posix() always gives forward slashes, even on Windows — plain os.path.join()
# gives backslashes there (e.g. C:\Users\...), which breaks the sqlite:/// URI format.
_default_db_path = (Path(BASE_DIR) / "timex.db").as_posix()
DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{_default_db_path}"

# NOTE: DATABASE_URL can be swapped for a PostgreSQL URL, e.g.
#   postgresql://user:password@localhost:5432/timexnepal
# with zero code changes elsewhere, since all queries go through SQLAlchemy's ORM.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine_kwargs = {"connect_args": connect_args, "pool_pre_ping": True}
if DATABASE_URL.startswith("postgresql"):
    engine_kwargs.update(pool_size=int(os.environ.get("DB_POOL_SIZE", "10")), max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "20")))
engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
