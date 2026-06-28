from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import UserStats, Vote, Question

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


class LeaderboardEntry(BaseModel):
    rank: int
    device_id: str
    correct_this_week: int
    total_this_week: int
    accuracy: float
    streak: int


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]
    week_start: str
    week_end: str
    player_rank: int | None


@router.get("/week", response_model=LeaderboardResponse)
async def get_weekly_leaderboard(device_id: str, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    # Week starts Monday
    week_start = (now - timedelta(days=now.weekday())).date()
    week_end = week_start + timedelta(days=6)

    # Aggregate correct votes per device this week
    majority_subq = (
        select(
            Question.id.label("qid"),
            func.case(
                (Question.votes_a >= Question.votes_b, "a"),
                else_="b",
            ).label("majority"),
        )
        .where(and_(Question.date >= week_start, Question.date <= week_end))
        .subquery()
    )

    weekly_stats = (
        select(
            Vote.device_id,
            func.count(Vote.id).label("total_this_week"),
            func.sum(
                func.cast(Vote.choice == majority_subq.c.majority, db.bind.dialect.name == "postgresql" and "integer" or "integer")
            ).label("correct_this_week"),
        )
        .join(majority_subq, Vote.question_id == majority_subq.c.qid)
        .where(
            Vote.created_at >= datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
        )
        .group_by(Vote.device_id)
        .order_by(func.sum(func.cast(Vote.choice == majority_subq.c.majority, "integer")).desc())
        .limit(100)
        .subquery()
    )

    result = await db.execute(select(weekly_stats))
    rows = result.fetchall()

    stats_map: dict[str, UserStats] = {}
    if rows:
        device_ids = [r.device_id for r in rows]
        stats_result = await db.execute(
            select(UserStats).where(UserStats.device_id.in_(device_ids))
        )
        for s in stats_result.scalars():
            stats_map[s.device_id] = s

    entries: list[LeaderboardEntry] = []
    player_rank: int | None = None

    for rank, row in enumerate(rows, start=1):
        correct = int(row.correct_this_week or 0)
        total = int(row.total_this_week or 0)
        accuracy = round(correct / total * 100, 1) if total else 0.0
        streak = stats_map.get(row.device_id, UserStats()).streak

        entries.append(
            LeaderboardEntry(
                rank=rank,
                device_id=row.device_id,
                correct_this_week=correct,
                total_this_week=total,
                accuracy=accuracy,
                streak=streak,
            )
        )
        if row.device_id == device_id:
            player_rank = rank

    return LeaderboardResponse(
        entries=entries,
        week_start=week_start.isoformat(),
        week_end=week_end.isoformat(),
        player_rank=player_rank,
    )
