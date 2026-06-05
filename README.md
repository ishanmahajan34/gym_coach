# Coach — personal gym webapp + bot

Your personal gym coach. Webapp on your phone for logging and viewing,
Telegram bot for nudges and check-ins. Free to host (Oracle Cloud + Cloudflare Tunnel).

This repo currently implements **Milestones 1-3**:

- ✅ **M1**: FastAPI skeleton, dark-themed PWA-ready frontend
- ✅ **M2**: Workout logging end-to-end (start, log sets, finish, rate)
- ✅ **M3**: Smart planner — generates push / pull / legs-light / conditioning rotations from history, with progressive overload
- ⏳ **M4**: Telegram bot (stub in place, env vars ready)
- ⏳ **M5**: Scheduler (morning / evening / Sunday nudges)
- ⏳ **M6**: Gemini polish on coach voice
- ⏳ **M7**: Oracle Cloud deploy + Cloudflare Tunnel

You can already use this as a personal gym log / coach without the bot or scheduling.

---

## Run it locally

```bash
# 1. Get Python 3.11+
python3 --version

# 2. Create a venv (recommended)
python3 -m venv .venv
source .venv/bin/activate         # macOS/Linux
# .venv\Scripts\activate          # Windows

# 3. Install
pip install -e .                   # uses pyproject.toml

# 4. Set up environment
cp .env.example .env
# Edit .env — for local dev you only need SECRET_KEY.
# Generate one: python -c "import secrets; print(secrets.token_urlsafe(32))"

# 5. Run
uvicorn app.main:app --reload

# 6. Open http://localhost:8000
```

First time: hit `/`, click "Plan today" — generates your first session. Click "Start session", log your sets (each set saves on change via HTMX), tap "Finish session", rate it.

---

## What it does today

**Home screen (`/`)**
- Today's planned workout (or empty state with "Plan today" button)
- Streak, this-week count (target 4), all-time
- Inspirational thought from a curated, non-gym-bro library

**Workout logging (`/workout/{id}`)**
- Each exercise grouped, last performance shown
- Tap into weight + reps fields, auto-save on change (HTMX, no page reload)
- "Finish session" → 1-5 rating + optional notes

**History (`/history`)**
- Last 21 days, ratings, durations

**Week plan (`/plan/week`)**
- Pre-commit days for the week (M-Sun checkboxes)

**The planner** (in `app/domain/planner.py`)
- Decides workout type from your history: never repeats back-to-back, forces legs after 8 days, throws in conditioning ~once a week
- Picks exercises avoiding ones used in the last 10 days
- Each push session: chest compound + shoulders compound + chest iso + shoulders iso + triceps
- Each pull session: 2 back compounds + back iso + rear delts + biceps
- Legs-light is short and varied (3 exercises, 45 min total)
- Conditioning days are bike intervals / incline walk / treadmill intervals

**Progression** (in `app/domain/progression.py`)
- Suggests next session's target weight from last performance
- +5 lb if you hit reps and rated ≥4, repeat if rated 3, repeat if you missed reps

---

## Project layout

```
gym_coach/
├── pyproject.toml           Dependencies + tooling
├── .env.example             Environment template
├── README.md                You are here
│
├── app/
│   ├── main.py              FastAPI app, lifespan (boots bot+scheduler when configured)
│   ├── config.py            Pydantic settings (reads .env)
│   ├── deps.py              Shared FastAPI dependencies
│   │
│   ├── db/
│   │   ├── engine.py        Async SQLAlchemy engine + session factory
│   │   └── models.py        ORM: User, Workout, WorkoutSet, WeekPlan, Reflection, AuthToken
│   │
│   ├── domain/              Pure logic — no FastAPI/Telegram imports
│   │   ├── exercises.py     Exercise catalog (data only)
│   │   ├── planner.py       Generates a WorkoutPlan from history
│   │   ├── progression.py   Suggests next-session weights
│   │   ├── workouts.py      Repository: CRUD + queries
│   │   └── stats.py         Streak, weekly count, total
│   │
│   ├── coach/
│   │   ├── inspiration.py   Curated thoughts library
│   │   ├── voice.py         (M6: tone templates, message builders)
│   │   └── llm.py           (M6: Gemini wrapper)
│   │
│   ├── web/
│   │   ├── routes/          home, workout, history, plan
│   │   ├── templates/       Jinja2 + HTMX
│   │   └── static/          CSS, manifest, service worker, icons
│   │
│   ├── bot/                 (M4) Telegram handlers
│   └── scheduler/           (M5) APScheduler jobs
│
├── tests/
│   └── test_planner.py
│
└── deploy/
    └── (M7) Cloudflare Tunnel + Oracle Cloud notes
```

---

## Design decisions worth knowing

**Async-everything.** FastAPI, SQLAlchemy 2.0 async, aiosqlite. The Telegram bot (`python-telegram-bot` v21+) and APScheduler are async-native too, so when M4 + M5 land, everything shares one event loop in one process.

**Single process.** Webapp + bot + scheduler all run in one container. `app/main.py` lifespan starts/stops them together. No IPC, no race conditions, no microservices.

**Domain logic is pure.** `app/domain/` and `app/coach/` don't import FastAPI or Telegram. Web routes and bot handlers both call into them. Means when you want a CLI, a web dashboard, or a different bot, the brain is reusable.

**Sets store target *and* actual.** `WorkoutSet.target_reps/weight` (the plan) vs `actual_reps/weight` (what you did). Keeps the prescribed-vs-executed distinction so progression logic is correct.

**Single-user for now.** `get_current_user()` returns a "default" user. When the bot lands at M4, it'll mint a magic-link via Telegram and we'll have proper auth. Architecture supports multi-user already (every table has user_id).

**HTMX everywhere.** Almost no JS. Each "log a set" is a tiny POST that returns just the updated row partial — feels instant, no page reloads. Total JS in the app: a 10-line service worker.

---

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

---

## Next milestones (rough order)

**M4 — Telegram bot.** `/start` mints a magic-link and DMs it back. `/today`, `/done`, `/skip`, `/streak`. Handlers call directly into `app.domain.*`.

**M5 — Scheduler.** APScheduler with 3 cron jobs:
- Morning (configurable hour) → generate today's plan if missing, send Telegram with link
- Evening → "how'd it go?" reflection prompt
- Sunday evening → week-ahead pre-commitment prompt

**M6 — Coach voice via Gemini.** Wraps planner output with conversational, varied messaging. Falls back cleanly to rule-based if API down or quota hit. Pulls from `inspiration.py` for thought-of-the-day.

**M7 — Deploy.** Dockerfile + docker-compose. Cloudflare Tunnel for HTTPS without port forwarding. Oracle Cloud ARM free tier setup notes in `deploy/oracle_setup.md`.

**M8+ — Extensions.** Calendar integration, body weight tracking, exercise progression charts, multi-user.

---

## A note on units

Per your preference: weights logged in **lb**, body metrics in **kg**. The DB stores raw numbers; UI labels are in `app/web/templates/`.
