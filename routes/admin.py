"""Minimal admin route to seed questions — protect with your own auth in prod."""
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import Question

router = APIRouter(prefix="/admin", tags=["admin"])


class QuestionIn(BaseModel):
    text: str
    option_a: str
    option_b: str
    emoji_a: str
    emoji_b: str
    date: date


def _require_secret(x_admin_key: str = Header(...)):
    if x_admin_key != settings.secret_key:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/question", dependencies=[Depends(_require_secret)], status_code=201)
async def create_question(payload: QuestionIn, db: AsyncSession = Depends(get_db)):
    q = Question(**payload.model_dump())
    db.add(q)
    await db.flush()
    return {"id": q.id, "date": q.date}


@router.patch("/question/{question_id}", dependencies=[Depends(_require_secret)])
async def update_question(question_id: int, payload: QuestionIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    for field, value in payload.model_dump().items():
        setattr(q, field, value)
    await db.flush()
    return {"id": q.id, "date": q.date}


@router.delete("/question/{question_id}", dependencies=[Depends(_require_secret)], status_code=204)
async def delete_question(question_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    await db.delete(q)
    await db.flush()
