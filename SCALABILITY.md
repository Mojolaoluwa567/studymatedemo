# Scalability Notes — targeting ~1,000 users

These are the changes worth making before/around 1,000 users, roughly in
priority order. None of this requires re-architecting the app — it's all
incremental on top of the current Flask + SQLAlchemy + React setup.

## 1. Database: move off SQLite (highest priority)

SQLite is fine for development and demos, but it serializes writes at the
file level - under concurrent users submitting quizzes, generating AI
content, etc., you'll see "database is locked" errors well before 1,000
users.

**Fix**: switch `DATABASE_URL` to a managed Postgres instance (Render,
Supabase, or Neon all have free tiers sufficient for this scale). Because
the app uses SQLAlchemy throughout, this is a **one-line config change** —
no code changes needed. Just run `db.create_all()` once against the new
database (or better, introduce Flask-Migrate at this point so future schema
changes are tracked properly instead of relying on `create_all`).

## 2. Add indexes on foreign keys

SQLite/SQLAlchemy don't automatically index foreign key columns. The
queries that will run most often — "all attempts for this user",
"all questions for this quiz", "all documents for this user" — benefit from
explicit indexes:

```python
# models.py
user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
```

Add `index=True` to: `Document.user_id`, `Quiz.user_id`, `Quiz.document_id`,
`Question.quiz_id`, `Attempt.user_id`, `Attempt.quiz_id`, `Answer.attempt_id`,
`StudySession.user_id`, `StudySession.document_id`, `Achievement.user_id`.
This is cheap and has no downside at this scale.

## 3. Protect the Gemini free-tier quota with rate limiting

The free Gemini tier has daily request caps shared across **all** your
users. A single user spamming "Generate quiz" or "Explain my mistakes"
could exhaust the quota for everyone.

**Fix**: add `Flask-Limiter` (one new dependency) and rate-limit the
AI-calling endpoints per user:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")

@app.route("/quizzes", methods=["POST"])
@limiter.limit("10 per hour")
@jwt_required()
def create_quiz():
    ...
```

Apply similar limits to `/attempts/<id>/explain`,
`/documents/<id>/summary|key-concepts|flashcards`, and `/forgot-password`
(to prevent reset-email spam). `storage_uri="memory://"` is fine for a
single server instance; if you ever run multiple instances, point it at
Redis instead.

## 4. Cache AI study aids more broadly

Summary/key-concepts/flashcards are already cached per-document on first
generation (Phase 4) — this is the single biggest cost-saver, since these
are the only "expensive" calls in the app. No further action needed unless
you add per-user variants of these (e.g. personalized summaries), in which
case cache per (user, document) instead of per document.

## 5. Static config endpoints

`GET /quizzes/config` returns constants that never change at runtime. At
1,000 users this is negligible, but if you introduce a CDN/reverse proxy
(e.g. when moving off Render's free tier), add a `Cache-Control: max-age=3600`
header to this response — it's a zero-risk win.

## 6. PDF upload limits and storage

`MAX_CONTENT_LENGTH` is already capped at 16MB. At 1,000 users storing full
PDF text in Postgres `TEXT` columns is fine size-wise, but if users start
uploading very large/many documents, consider:
- Truncating `text_content` storage (not just the prompt) to a reasonable
  cap (e.g. 100k chars) — full textbooks aren't needed for quiz generation
  anyway.
- If you ever need the original PDF files (not just extracted text) for a
  feature, store them in object storage (S3/Cloudflare R2), not the
  database or local disk (Render's disk is ephemeral).

## 7. Security hardening checklist

- Ensure `SECRET_KEY` / `JWT_SECRET_KEY` are long random values in
  production (covered earlier) — never the `.env.example` defaults.
- Set JWT access token expiry (Flask-JWT-Extended defaults to 15 minutes,
  which is fine; just confirm it's not been overridden to "never expire").
- `/forgot-password` already returns a generic message regardless of
  whether the email exists (prevents account enumeration) — keep this
  pattern for any future user-lookup endpoints.
- CORS is already locked to `FRONTEND_ORIGIN` — don't widen this to `*` in
  production.

## 8. What NOT to do yet

At 1,000 users, you do **not** need: a task queue (Celery/RQ) for AI calls
(synchronous requests are fine — Gemini responses return in a few seconds),
microservices, Kubernetes, or a separate read replica. These add ongoing
operational complexity that isn't justified until you're seeing real
concurrency issues in production metrics. Revisit if/when you exceed
~10,000 users or notice request queuing under load.

## Summary — do these 3 things first

1. Switch SQLite → Postgres (config change only).
2. Add `index=True` to foreign key columns.
3. Add Flask-Limiter on AI-calling endpoints.

Everything else on this list is "nice to have, low urgency" at this scale.
