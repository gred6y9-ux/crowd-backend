from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Question, UserStats, Vote

router = APIRouter(prefix="/vote", tags=["vote"])


class VoteRequest(BaseModel):
    device_id: str
    question_id: int
    choice: str

    @field_validator("choice")
    @classmethod
    def validate_choice(cls, v: str) -> str:
        v = v.lower()
        if v not in ("a", "b"):
            raise ValueError("choice must be 'a' or 'b'")
        return v

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, v: str) -> str:
        if not v or len(v) > 128:
            raise ValueError("invalid device_id")
        return v


class VoteResultResponse(BaseModel):
    choice: str
    percent_a: float
    percent_b: float
    votes_a: int
    votes_b: int
    total_votes: int
    is_majority: bool  # did the player pick the winning side
    streak: int
    total_correct: int
    total_played: int
    accuracy: float


@router.post("/", response_model=VoteResultResponse)
async def cast_vote(payload: VoteRequest, db: AsyncSession = Depends(get_db)):
    today = datetime.now(timezone.utc).date()

    result = await db.execute(
        select(Question).where(Question.id == payload.question_id)
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.date != today:
        raise HTTPException(status_code=400, detail="Voting is only allowed for today's question")

    existing = await db.execute(
        select(Vote).where(
            Vote.device_id == payload.device_id,
            Vote.question_id == payload.question_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already voted for today's question")

    vote = Vote(
        device_id=payload.device_id,
        question_id=payload.question_id,
        choice=payload.choice,
    )
    db.add(vote)

    if payload.choice == "a":
        question.votes_a += 1
    else:
        question.votes_b += 1

    stats_result = await db.execute(
        select(UserStats).where(UserStats.device_id == payload.device_id)
    )
    stats = stats_result.scalar_one_or_none()

    if not stats:
        stats = UserStats(device_id=payload.device_id)
        db.add(stats)

    # Determine majority before counting this vote so we compare against the crowd
    # Actually we count this vote first, then check majority — player is part of the crowd
    total = question.votes_a + question.votes_b
    majority_choice = "a" if question.votes_a >= question.votes_b else "b"
    is_majority = payload.choice == majority_choice

    stats.total_played += 1
    if is_majority:
        stats.total_correct += 1

    # Streak logic
    yesterday = today - timedelta(days=1)
    if stats.last_played == yesterday:
        stats.streak += 1
    elif stats.last_played == today:
        pass  # already played today (shouldn't happen due to duplicate check above)
    else:
        stats.streak = 1

    stats.last_played = today

    await db.flush()

    percent_a = round(question.votes_a / total * 100, 1) if total else 0.0
    percent_b = round(question.votes_b / total * 100, 1) if total else 0.0
    accuracy = round(stats.total_correct / stats.total_played * 100, 1) if stats.total_played else 0.0

    return VoteResultResponse(
        choice=payload.choice,
        percent_a=percent_a,
        percent_b=percent_b,
        votes_a=question.votes_a,
        votes_b=question.votes_b,
        total_votes=total,
        is_majority=is_majority,
        streak=stats.streak,
        total_correct=stats.total_correct,
        total_played=stats.total_played,
        accuracy=accuracy,
    )
