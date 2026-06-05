"""Run: python -m scripts.migrate_v2"""
import asyncio
from sqlalchemy import text
from app.db.engine import engine

STATEMENTS = [
    "ALTER TABLE workouts ADD COLUMN cardio_minutes_low INTEGER",
    "ALTER TABLE workouts ADD COLUMN cardio_minutes_high INTEGER",
    "UPDATE workouts SET type = 'squat' WHERE type = 'legs_light'",
    """
    CREATE TABLE IF NOT EXISTS daily_habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        date DATE NOT NULL,
        stretch_done BOOLEAN NOT NULL DEFAULT 0,
        stretch_minutes INTEGER,
        stretch_logged_at DATETIME,
        balance_done BOOLEAN NOT NULL DEFAULT 0,
        balance_minutes INTEGER,
        balance_logged_at DATETIME,
        walk_breakfast_at DATETIME,
        walk_lunch_at DATETIME,
        walk_dinner_at DATETIME,
        CONSTRAINT uq_habit_user_date UNIQUE (user_id, date)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_daily_habits_user_id ON daily_habits(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_daily_habits_date ON daily_habits(date)",
]


async def main():
    async with engine.begin() as conn:
        for stmt in STATEMENTS:
            try:
                await conn.execute(text(stmt))
                print(f"OK: {stmt.strip()[:60]}")
            except Exception as e:
                print(f"SKIP (likely exists): {e}")


asyncio.run(main())
