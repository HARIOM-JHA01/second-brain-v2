import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from agente_rolplay.db.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    settings = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="owned_organizations")
    profiles = relationship(
        "Profile", back_populates="organization", cascade="all, delete-orphan"
    )
    roles = relationship(
        "Role", back_populates="organization", cascade="all, delete-orphan"
    )
    documents = relationship(
        "Document", back_populates="organization", cascade="all, delete-orphan"
    )
    coaching_scenarios = relationship(
        "CoachingScenario", back_populates="organization", cascade="all, delete-orphan"
    )


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    profiles = relationship(
        "Profile", back_populates="user", cascade="all, delete-orphan"
    )
    owned_organizations = relationship("Organization", back_populates="owner")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    whatsapp_number = Column(String(50), nullable=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="profiles")
    organization = relationship("Organization", back_populates="profiles")
    role = relationship("Role", back_populates="profiles")


class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(100), nullable=False)
    permissions = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="roles")
    profiles = relationship("Profile", back_populates="role")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=True)
    drive_file_id = Column(String(255), nullable=True)
    # Data Store / Knowledge Base split
    location = Column(String(20), default="knowledgebase")   # "datastore" | "knowledgebase"
    cloudinary_url = Column(Text, nullable=True)             # stored directly to avoid extra API calls
    file_type = Column(String(50), nullable=True)            # pdf, docx, image, etc.
    file_size = Column(Integer, nullable=True)               # bytes
    resource_type = Column(String(20), nullable=True)        # "raw" | "image"
    uploaded_by = Column(String(100), nullable=True)         # phone number or "admin"
    upload_source = Column(String(20), default="whatsapp")   # "whatsapp" | "web"
    vector_id = Column(String(255), nullable=True)           # first Pinecone chunk ID (when in KB)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="documents")


class CoachingScenario(Base):
    __tablename__ = "coaching_scenarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    system_prompt = Column(Text, nullable=False)
    reference_file_name = Column(String(255), nullable=True)
    reference_file_text = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    usecase_api_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="coaching_scenarios")
    sessions = relationship(
        "CoachingSession", back_populates="scenario", passive_deletes=True
    )
    reference_files = relationship(
        "CoachingScenarioReferenceFile",
        back_populates="scenario",
        cascade="all, delete-orphan",
    )


class CoachingSession(Base):
    __tablename__ = "coaching_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=True)
    phone_number = Column(String(50), nullable=False)
    scenario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("coaching_scenarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    scenario_name = Column(String(255), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    report_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    scenario = relationship("CoachingScenario", back_populates="sessions")


class CoachingScenarioReferenceFile(Base):
    __tablename__ = "coaching_scenario_reference_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("coaching_scenarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_name = Column(String(255), nullable=False)
    file_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    scenario = relationship("CoachingScenario", back_populates="reference_files")


class MessageLog(Base):
    __tablename__ = "message_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=True)  # null if phone not registered
    phone_number = Column(String(50), nullable=False)
    message_type = Column(String(20), default="text")  # text, audio, image, document
    is_voice_note = Column(Boolean, default=False)
    is_rag_query = Column(Boolean, default=False)
    response_time_ms = Column(Integer, nullable=True)
    is_error = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=True)  # null if phone not registered
    phone_number = Column(String(50), nullable=False, index=True)
    role = Column(String(10), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")  # text, audio, image, document
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
