import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import Base, engine
from routes.admin import router as admin_router
from routes.battle import router as battle_router
from routes.leaderboard import router as leaderboard_router
from routes.questions import router as questions_router
from routes.votes import router as votes_router
from services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    start_scheduler()
    yield
    stop_scheduler()
    await engine.dispose()


app = FastAPI(
    title="CROWD API",
    version="1.0.0",
    description="Daily crowd-prediction game backend",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(questions_router)
app.include_router(votes_router)
app.include_router(leaderboard_router)
app.include_router(admin_router)
app.include_router(battle_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
