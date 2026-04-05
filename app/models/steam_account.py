from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SteamAccount(TimestampMixin, Base):
    __tablename__ = "steam_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    steam_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    shared_secret_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    identity_secret_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    revocation_code_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    steam_session_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    session_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="steam_accounts")  # noqa: F821

    def __str__(self) -> str:
        return self.account_name
