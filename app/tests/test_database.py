from shared.config import settings
from shared.database import engine, get_db


def test_engine_is_created():
    assert str(engine.url) == settings.DATABASE_URL


# checks if the get function returns a session
def test_get_db_yield_a_session():
    gen = get_db()
    session = next(gen)
    assert session is not None
    session.close()


# check whether it can connect to the db
def test_engine_can_connect():
    with engine.connect() as connection:
        assert connection.dialect.do_ping(connection.connection)
