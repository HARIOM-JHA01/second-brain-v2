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
    "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS settings JSONB DEFAULT '{}'",
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
    # Data Store / Knowledge Base split columns on documents table
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS location VARCHAR(20) DEFAULT 'knowledgebase'",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS cloudinary_url TEXT",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_type VARCHAR(50)",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_size INTEGER",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS resource_type VARCHAR(20)",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS uploaded_by VARCHAR(100)",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS upload_source VARCHAR(20) DEFAULT 'whatsapp'",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS vector_id VARCHAR(255)",
    "CREATE INDEX IF NOT EXISTS idx_documents_location ON documents(location)",
    "CREATE INDEX IF NOT EXISTS idx_documents_org_location ON documents(org_id, location)",
    # Groups and Broadcast tables
    """
        CREATE TABLE IF NOT EXISTS groups (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            org_id UUID REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
            name VARCHAR(255) NOT NULL,
            created_by_id UUID REFERENCES users(id),
            created_at TIMESTAMP DEFAULT now()
        )
    """,
    """
        CREATE TABLE IF NOT EXISTS group_members (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            group_id UUID REFERENCES groups(id) ON DELETE CASCADE NOT NULL,
            user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
            profile_id UUID,
            created_at TIMESTAMP DEFAULT now()
        )
    """,
    """
        CREATE TABLE IF NOT EXISTS message_templates (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            org_id UUID REFERENCES organizations(id),
            name VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            variables JSONB DEFAULT '[]',
            is_active BOOLEAN DEFAULT true,
            created_by_id UUID REFERENCES users(id),
            created_at TIMESTAMP DEFAULT now()
        )
    """,
    """
        CREATE TABLE IF NOT EXISTS broadcast_schedules (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            org_id UUID REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
            template_id UUID REFERENCES message_templates(id) ON DELETE SET NULL,
            group_id UUID REFERENCES groups(id) ON DELETE SET NULL,
            scheduled_at TIMESTAMP NOT NULL,
            variable_values JSONB DEFAULT '{}',
            status VARCHAR(20) DEFAULT 'pending',
            sent_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            created_by_id UUID REFERENCES users(id),
            created_at TIMESTAMP DEFAULT now(),
            sent_at TIMESTAMP
        )
    """,
]


def init_db():
    from agente_rolplay.db import models

    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        for stmt in _MIGRATIONS:
            conn.execute(text(stmt))
        conn.commit()
    print("[init_db] Migrations applied successfully.")
