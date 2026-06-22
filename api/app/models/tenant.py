import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="tenant")
    configs = relationship("TenantConfig", back_populates="tenant", uselist=False)


class TenantConfig(Base):
    __tablename__ = "tenant_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    backend_type: Mapped[str] = mapped_column(String(50), default="apex")
    config_json: Mapped[str] = mapped_column(String, default="{}")
    fusion_user: Mapped[str] = mapped_column(String(255), default="")
    fusion_pass: Mapped[str] = mapped_column(String(255), default="")
    fusion_apex_id: Mapped[str] = mapped_column(String(100), default="")
    agent_api_key: Mapped[str] = mapped_column(String(255), default="")
    nemo_api_key: Mapped[str] = mapped_column(String(512), default="")
    nemo_provider: Mapped[str] = mapped_column(String(50), default="deepseek")
    nemo_model: Mapped[str] = mapped_column(String(100), default="deepseek-chat")
    nemo_configured: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="configs")
