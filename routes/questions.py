from datetime import date, timezone, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Question, UserStats

router = APIRouter(prefix="/question", tags=["question"])


class QuestionResponse(BaseModel):
    id: int
    text: str
    option_a: str
    option_b: str
    emoji_a: str
    emoji_b: str
    date: date
    total_votes: int

    model_config = {"from_attributes": True}


class PlayerStatusResponse(BaseModel):
    question: QuestionResponse
    already_voted: bool
    voted_choice: str | None
    streak: int
    total_played: int
    total_correct: int
    accuracy: float


@router.get("/today", response_model=PlayerStatusResponse)
async def get_today_question(device_id: str, db: AsyncSession = Depends(get_db)):
    today = datetime.now(timezone.utc).date()

    result = await db.execute(select(Question).where(Question.date == today))
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="No question scheduled for today")

    stats_result = await db.execute(
        select(UserStats).where(UserStats.device_id == device_id)
    )
    stats = stats_result.scalar_one_or_none()

    if not stats:
        stats = UserStats(device_id=device_id)
        db.add(stats)
        await db.flush()

    from models import Vote
    vote_result = await db.execute(
        select(Vote).where(Vote.device_id == device_id, Vote.question_id == question.id)
    )
    existing_vote = vote_result.scalar_one_or_none()

    accuracy = 0.0
    if stats.total_played > 0:
        accuracy = round(stats.total_correct / stats.total_played * 100, 1)

    return PlayerStatusResponse(
        question=QuestionResponse(
            id=question.id,
            text=question.text,
            option_a=question.option_a,
            option_b=question.option_b,
            emoji_a=question.emoji_a,
            emoji_b=question.emoji_b,
            date=question.date,
            total_votes=question.votes_a + question.votes_b,
        ),
        already_voted=existing_vote is not None,
        voted_choice=existing_vote.choice if existing_vote else None,
        streak=stats.streak,
        total_played=stats.total_played,
        total_correct=stats.total_correct,
        accuracy=accuracy,
    )
