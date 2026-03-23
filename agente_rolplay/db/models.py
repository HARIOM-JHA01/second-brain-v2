import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, JSON, Text
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
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="coaching_scenarios")
    sessions = relationship(
        "CoachingSession", back_populates="scenario", passive_deletes=True
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
