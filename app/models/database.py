"""Database models for IntentAPI"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship, DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class PlanTier(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    PARSING = "parsing"
    EXECUTING = "executing"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255))
    company = Column(String(255))
    plan = Column(SQLEnum(PlanTier), default=PlanTier.FREE)
    stripe_customer_id = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    executions = relationship("Execution", back_populates="user", cascade="all, delete-orphan")
    connectors = relationship("UserConnector", back_populates="user", cascade="all, delete-orphan")


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    key_prefix = Column(String(12), nullable=False)  # First 8 chars for identification
    name = Column(String(255), default="Default Key")
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="api_keys")

    __table_args__ = (Index("idx_api_key_hash", "key_hash"),)


class UserConnector(Base):
    __tablename__ = "user_connectors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    connector_type = Column(String(50), nullable=False)  # e.g., "gmail", "slack", "stripe"
    config_encrypted = Column(Text)  # Encrypted JSON config
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="connectors")


class Execution(Base):
    __tablename__ = "executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    intent_raw = Column(Text, nullable=False)  # Original natural language input
    intent_parsed = Column(JSON)  # Structured action graph
    status = Column(SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING)
    result = Column(JSON)
    error = Column(Text)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    execution_time_ms = Column(Integer)
    require_approval = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime)

    user = relationship("User", back_populates="executions")
    steps = relationship("ExecutionStep", back_populates="execution", cascade="all, delete-orphan")


class ExecutionStep(Base):
    __tablename__ = "execution_steps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id = Column(String, ForeignKey("executions.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    connector_type = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    input_data = Column(JSON)
    output_data = Column(JSON)
    status = Column(SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING)
    error = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    execution = relationship("Execution", back_populates="steps")


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    endpoint = Column(String(255), nullable=False)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("idx_usage_user_date", "user_id", "created_at"),)
