from shared.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(settings.DATABASE_URL)

Session = sessionmaker(engine)


# with Session() as s:
def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
