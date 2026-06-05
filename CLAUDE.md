# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Coach — personal gym webapp + bot

Personal project for Ishan. Telegram bot + FastAPI webapp for workout
tracking and motivation. Built for weight loss focus, intermediate lifter,
basic gym (dumbbells/machines/cardio), 45-60 min sessions, light on legs.

## Stack
- FastAPI (async) + Jinja2 + HTMX
- SQLAlchemy 2.0 async + SQLite (aiosqlite)
- python-telegram-bot v21+ async
- APScheduler async
- Google Gemini API (free tier) for coach voice polish
- Single-process: webapp + bot + scheduler share one event loop

## Architecture principles
- Domain logic in app/domain/* and app/coach/* is pure — no FastAPI/Telegram imports
- Web routes and bot handlers both call into domain layer
- Async everything from day one
- Single user for now; user_id columns already in place for multi-user later

## Milestones
- M1-M3 (DONE): webapp skeleton, workout logging, smart planner with progressive overload
- M4 (NEXT): Telegram bot — magic-link auth, /today /done /skip /streak commands
- M5: APScheduler — morning plan ping, evening check-in, Sunday pre-commit
- M6: Gemini polish on coach voice (with rule-based fallback)
- M7: Deploy to Oracle Cloud free tier, Cloudflare Tunnel for HTTPS

## Conventions
- Weights in lb, body metrics in kg
- Dark theme, Fraunces (serif headings) + Inter Tight (body) + JetBrains Mono (stats)
- Coaching voice: grounded, health-as-foundation, no gym-bro culture, Stoic-leaning
- No emojis in coaching messages unless user uses them

## Ishan's preferences
- "Mostly you build, I configure" but I'm an engineer who can read & modify code
- Light on legs (1 short legs day/week, never skipped fully)
- Inspiration sources: Stoic, athletes-with-balance, identity-based — NO Ronnie Coleman / aesthetic gym culture