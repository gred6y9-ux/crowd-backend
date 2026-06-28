from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    option_a: Mapped[str] = mapped_column(String(200), nullable=False)
    option_b: Mapped[str] = mapped_column(String(200), nullable=False)
    emoji_a: Mapped[str] = mapped_column(String(10), nullable=False)
    emoji_b: Mapped[str] = mapped_column(String(10), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    votes_a: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    votes_b: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    votes: Mapped[list["Vote"]] = relationship("Vote", back_populates="question")


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("device_id", "question_id", name="uq_device_question"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("questions.id"), nullable=False)
    choice: Mapped[str] = mapped_column(String(1), nullable=False)  # "a" or "b"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    question: Mapped["Question"] = relationship("Question", back_populates="votes")


class UserStats(Base):
    __tablename__ = "user_stats"

    device_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_played: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
