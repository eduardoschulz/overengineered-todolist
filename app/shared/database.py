from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.config import settings

_engine = None
_Session = None


def _setup():
    global _engine, _Session
    if _engine is None:
        _engine = create_engine(settings.DATABASE_URL)
        _Session = sessionmaker(_engine)


def get_db():
    _setup()
    db = _Session()
    try:
        yield db
    finally:
        db.close()
