from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session
from app.config import get_settings

class Base(DeclarativeBase):
    pass

@lru_cache
def get_engine():
    return create_engine(get_settings().sqlalchemy_url, pool_pre_ping=True,
                         pool_size=5, max_overflow=5, pool_timeout=5,
                         connect_args={"connect_timeout": 5, "options": "-c statement_timeout=10000"})

def get_db():
    with Session(get_engine()) as session:
        yield session
