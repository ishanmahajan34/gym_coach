"""FastAPI app entry. Run with: uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db.engine import init_db, close_db
from app.web.routes import home, workout, history, plan, habits, week


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Bot + scheduler will be wired in milestone 4-5; gated by config
    bot_app = None
    scheduler = None
    if settings.bot_enabled:
        from app.bot.runner import start_bot
        bot_app = await start_bot()
        app.state.bot = bot_app
    if settings.scheduler_enabled:
        from app.scheduler.runner import start_scheduler
        scheduler = start_scheduler(bot_app)
        app.state.scheduler = scheduler

    yield

    if scheduler:
        scheduler.shutdown()
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    await close_db()


app = FastAPI(title="Coach", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

app.include_router(home.router)
app.include_router(workout.router)
app.include_router(history.router)
app.include_router(habits.router)
app.include_router(week.router)
app.include_router(plan.router)  # kept for /plan/week redirect
