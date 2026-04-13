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
    """
        CREATE TABLE IF NOT EXISTS coaching_scenario_reference_files (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            scenario_id UUID REFERENCES coaching_scenarios(id) ON DELETE CASCADE,
            file_name VARCHAR(255) NOT NULL,
            file_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT now()
        )
    """,
    "ALTER TABLE coaching_scenarios ADD COLUMN IF NOT EXISTS usecase_api_id INTEGER",
    """
        CREATE TABLE IF NOT EXISTS whatsapp_messages (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            org_id UUID,
            phone_number VARCHAR(50) NOT NULL,
            role VARCHAR(10) NOT NULL,
            content TEXT NOT NULL,
            message_type VARCHAR(20) DEFAULT 'text',
            created_at TIMESTAMP DEFAULT now()
        )
    """,
    "CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_phone ON whatsapp_messages(phone_number)",
    "CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_created ON whatsapp_messages(created_at)",
]


def init_db():
    from agente_rolplay.db import models

    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        for stmt in _MIGRATIONS:
            conn.execute(text(stmt))
        conn.commit()
    print("[init_db] Migrations applied successfully.")
