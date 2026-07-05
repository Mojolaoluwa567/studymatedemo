"""
Admin dashboard data layer. Every figure here is DERIVED from existing
tables (User, Document, Quiz, Attempt, Answer) - there's no dedicated
"event log" or analytics table. This keeps the admin view honest about
what it can show: real counts of real rows, not synthetic tracking that
would need its own write-path threaded through every endpoint.

AI usage in particular is a proxy, not a metered count from the Gemini
API itself: every Quiz row represents at least one generation call, every
submitted Attempt with theory questions represents one grading call
(batched, so 1 call regardless of how many theory questions), and every
cached Document.summary/key_concepts/flashcards represents one call each,
ONCE per document since they're cached after first generation. This is
documented here explicitly so the number is never mistaken for "exact
Gemini quota consumed."
"""

from datetime import datetime, timedelta
from sqlalchemy import func

from extensions import db
from models import User, Document, Quiz, Attempt, Answer


def get_admin_overview():
    """High-level counts for the admin dashboard's top stat row."""
    total_users = User.query.count()
    total_students = User.query.filter_by(role="student").count()
    total_teachers = User.query.filter_by(role="teacher").count()
    total_documents = Document.query.count()
    total_quizzes = Quiz.query.count()
    total_attempts = Attempt.query.filter(Attempt.submitted_at.isnot(None)).count()

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    new_users_7d = User.query.filter(User.created_at >= seven_days_ago).count()
    active_users_7d = (
        db.session.query(Attempt.user_id)
        .filter(Attempt.submitted_at >= seven_days_ago)
        .distinct()
        .count()
    )

    avg_score = (
        db.session.query(func.avg(Attempt.percentage))
        .filter(Attempt.submitted_at.isnot(None))
        .scalar()
    )

    return {
        "total_users": total_users,
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_documents": total_documents,
        "total_quizzes": total_quizzes,
        "total_attempts": total_attempts,
        "new_users_7d": new_users_7d,
        "active_users_7d": active_users_7d,
        "platform_average_score": round(avg_score, 1) if avg_score else None,
    }


def get_admin_users(search=None, limit=200):
    """
    Every user with lightweight per-user activity counts, for the admin
    user list. Capped at `limit` rows - this is a dashboard view, not a
    paginated export; if the platform grows well past a few hundred
    users, this should gain real pagination (left as a known limitation,
    same honesty as the AI-usage proxy above).
    """
    query = User.query.order_by(User.created_at.desc())
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(User.username.ilike(like), User.email.ilike(like))
        )

    users = query.limit(limit).all()

    # Batch-fetch counts instead of N+1 querying per user.
    doc_counts = dict(
        db.session.query(Document.user_id, func.count(Document.id))
        .group_by(Document.user_id)
        .all()
    )
    attempt_counts = dict(
        db.session.query(Attempt.user_id, func.count(Attempt.id))
        .filter(Attempt.submitted_at.isnot(None))
        .group_by(Attempt.user_id)
        .all()
    )

    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "is_admin": u.is_admin,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "document_count": doc_counts.get(u.id, 0),
            "quiz_attempt_count": attempt_counts.get(u.id, 0),
        }
        for u in users
    ]


def get_admin_user_detail(user_id):
    """Full activity detail for one user - the drill-down view."""
    user = db.session.get(User, user_id)
    if not user:
        return None

    documents = (
        Document.query.filter_by(user_id=user_id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    attempts = (
        Attempt.query.filter_by(user_id=user_id)
        .filter(Attempt.submitted_at.isnot(None))
        .order_by(Attempt.submitted_at.desc())
        .all()
    )

    avg_score = (
        round(sum(a.percentage for a in attempts) / len(attempts), 1)
        if attempts
        else None
    )

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_admin": user.is_admin,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "average_score": avg_score,
        "documents": [
            {
                "id": d.id,
                "title": d.title,
                "source_type": d.source_type,
                "uploaded_at": d.uploaded_at.isoformat(),
            }
            for d in documents
        ],
        "recent_attempts": [
            {
                "id": a.id,
                "quiz_id": a.quiz_id,
                "difficulty": a.quiz.difficulty,
                "percentage": a.percentage,
                "submitted_at": a.submitted_at.isoformat(),
            }
            for a in attempts[:20]
        ],
    }


def get_admin_content(search=None, limit=200):
    """Every document platform-wide, with its owner, for content oversight."""
    query = (
        db.session.query(Document, User)
        .join(User, Document.user_id == User.id)
        .order_by(Document.uploaded_at.desc())
    )
    if search:
        like = f"%{search}%"
        query = query.filter(Document.title.ilike(like))

    rows = query.limit(limit).all()

    return [
        {
            "id": d.id,
            "title": d.title,
            "source_type": d.source_type,
            "page_count": d.page_count,
            "uploaded_at": d.uploaded_at.isoformat(),
            "owner_username": u.username,
            "owner_id": u.id,
        }
        for d, u in rows
    ]


def get_admin_usage():
    """
    AI-usage proxy and platform-wide quiz/score analytics. See module
    docstring for what "AI calls" means here - derived counts, not a
    metered total from Gemini's API.
    """
    total_quiz_generations = Quiz.query.count()  # 1 generation call each

    theory_grading_calls = (
        db.session.query(Attempt.id)
        .join(Quiz)
        .filter(Attempt.submitted_at.isnot(None))
        .join(Answer, Answer.attempt_id == Attempt.id)
        .filter(Answer.feedback.isnot(None))  # feedback is only set for theory answers
        .distinct()
        .count()
    )

    summaries_generated = Document.query.filter(
        Document.summary.isnot(None)
    ).count()
    key_concepts_generated = Document.query.filter(
        Document.key_concepts.isnot(None)
    ).count()
    flashcards_generated = Document.query.filter(
        Document.flashcards.isnot(None)
    ).count()

    explanations_generated = (
        db.session.query(Answer.id)
        .filter(Answer.explanation.isnot(None))
        .count()
    )

    estimated_total_ai_calls = (
        total_quiz_generations
        + theory_grading_calls
        + summaries_generated
        + key_concepts_generated
        + flashcards_generated
        + explanations_generated  # each explain-mistakes call is batched per attempt, but counting per-answer here is a deliberate overestimate margin - documented below
    )

    # Score distribution by difficulty - shows whether any tier is
    # systematically too easy/hard across the whole platform.
    by_difficulty = (
        db.session.query(
            Quiz.difficulty,
            func.count(Attempt.id),
            func.avg(Attempt.percentage),
        )
        .join(Attempt, Attempt.quiz_id == Quiz.id)
        .filter(Attempt.submitted_at.isnot(None))
        .group_by(Quiz.difficulty)
        .all()
    )

    # Last 14 days of attempt volume, for a simple activity trend.
    fourteen_days_ago = datetime.utcnow() - timedelta(days=14)
    daily_attempts = (
        db.session.query(
            func.date(Attempt.submitted_at),
            func.count(Attempt.id),
        )
        .filter(Attempt.submitted_at >= fourteen_days_ago)
        .filter(Attempt.submitted_at.isnot(None))
        .group_by(func.date(Attempt.submitted_at))
        .order_by(func.date(Attempt.submitted_at))
        .all()
    )

    return {
        "estimated_total_ai_calls": estimated_total_ai_calls,
        "breakdown": {
            "quiz_generations": total_quiz_generations,
            "theory_grading_batches": theory_grading_calls,
            "summaries_generated": summaries_generated,
            "key_concepts_generated": key_concepts_generated,
            "flashcards_generated": flashcards_generated,
            "explanations_generated": explanations_generated,
        },
        "score_by_difficulty": [
            {
                "difficulty": difficulty,
                "attempt_count": count,
                "average_percentage": round(avg, 1) if avg else None,
            }
            for difficulty, count, avg in by_difficulty
        ],
        "daily_attempts_last_14d": [
            {"date": str(date), "count": count} for date, count in daily_attempts
        ],
    }
