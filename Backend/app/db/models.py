from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship 
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Enum as SQLEnum
from datetime import datetime, UTC 

from enum import Enum 


class ProxyProtocol(str, Enum):
    SOCKS = "socks5"
    HTTP = "http"
    HTTPS = "https"


class Model(DeclarativeBase):
    pass


class Admin(Model):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class User(Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=False, nullable=False)
    activation_key: Mapped[str | None] = mapped_column(unique=True, nullable=True, index = True)
    activation_key_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda : datetime.now(UTC),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda : datetime.now(UTC), 
        onupdate=lambda : datetime.now(UTC), 
        nullable=False
    )
    virtual_machines: Mapped[list["VirtualMachine"]] = relationship(back_populates = "current_user")


class VirtualMachine(Model):
    __tablename__ = "virtual_machines"
    __table_args__ = (
        UniqueConstraint("host", "port", name="uq_virtual_machines_host_port"),
    )

    id : Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
    host: Mapped[str] = mapped_column(nullable=False)
    port: Mapped[int] = mapped_column(nullable=False)
    protocol: Mapped[ProxyProtocol] = mapped_column(
        SQLEnum(ProxyProtocol),
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default = True, nullable=False)
    current_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index = True,  unique=True, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_user: Mapped["User | None"] = relationship(
        back_populates="virtual_machines"
    )




