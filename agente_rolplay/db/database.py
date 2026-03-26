from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from agente_rolplay.config import DATABASE_URL

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_MIGRATIONS = [
    "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)",
    "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS job_title VARCHAR(255)",
    "ALTER TABLE coaching_scenarios ADD COLUMN IF NOT EXISTS reference_file_name VARCHAR(255)",
    "ALTER TABLE coaching_scenarios ADD COLUMN IF NOT EXISTS reference_file_text TEXT",
]


def init_db():
    from agente_rolplay.db import models

    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        for stmt in _MIGRATIONS:
            conn.execute(text(stmt))
        conn.commit()
