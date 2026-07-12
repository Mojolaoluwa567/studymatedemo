"""
Achievement definitions and the logic to check/unlock them.

Achievements are intentionally derived from data that already exists
(Attempt, Answer, StudySession) - no extra tracking tables beyond the
Achievement unlock record itself.
"""

from datetime import datetime, timedelta

from extensions import db
from models import (
    Attempt,
    StudySession,
    Achievement,
    Quiz,
    Class,
    ClassMembership,
)


ACHIEVEMENTS = {
    "first_quiz": {
        "title": "First Quiz Completed",
        "description": "Complete your first quiz.",
    },
    "hundred_questions": {
        "title": "Centurion",
        "description": "Answer 100 questions in total.",
    },
    "perfect_score": {
        "title": "Perfect Score",
        "description": "Score 100% on a quiz.",
    },
    "seven_day_streak": {
        "title": "7-Day Streak",
        "description": "Study or take a quiz for 7 days in a row.",
    },
}


TEACHER_ACHIEVEMENTS = {
    "first_class": {
        "title": "Classroom Founded",
        "description": "Create your first class.",
    },
    "ten_students": {
        "title": "Growing Cohort",
        "description": "Reach 10 students enrolled across your classes.",
    },
    "fifty_students": {
        "title": "Full House",
        "description": "Reach 50 students enrolled across your classes.",
    },
    "first_assignment_published": {
        "title": "First Assignment Live",
        "description": "Publish your first assignment.",
    },
    "five_assignments_published": {
        "title": "Prolific Educator",
        "description": "Publish 5 assignments.",
    },
}


def compute_stats(user_id):
    """Shared stats used by /profile/stats and achievement checks."""
    attempts = (
        Attempt.query.filter_by(user_id=user_id)
        .filter(Attempt.submitted_at.isnot(None))
        .all()
    )
    total_quizzes = len(attempts)
    total_questions = sum(a.quiz.num_questions for a in attempts)
    average_score = (
        round(sum(a.percentage for a in attempts) / total_quizzes, 1)
        if total_quizzes
        else 0
    )
    has_perfect_score = any(a.percentage == 100 for a in attempts)

    study_dates = {
        s.started_at.date()
        for s in StudySession.query.filter_by(user_id=user_id).all()
    }
    attempt_dates = {a.submitted_at.date() for a in attempts}
    active_dates = study_dates | attempt_dates

    streak = 0
    today = datetime.utcnow().date()
    cursor = today
    if cursor not in active_dates:
        cursor -= timedelta(days=1)
    while cursor in active_dates:
        streak += 1
        cursor -= timedelta(days=1)

    return {
        "total_quizzes": total_quizzes,
        "total_questions_answered": total_questions,
        "average_score": average_score,
        "current_streak": streak,
        "has_perfect_score": has_perfect_score,
    }


def check_and_unlock_achievements(user_id):
    """
    Checks current stats against achievement criteria, unlocks any newly
    earned ones (persisting Achievement rows), and returns a list of
    {key, title, description} for achievements unlocked by THIS call.
    """
    stats = compute_stats(user_id)
    existing_keys = {
        a.key for a in Achievement.query.filter_by(user_id=user_id).all()
    }

    to_unlock = []
    if stats["total_quizzes"] >= 1 and "first_quiz" not in existing_keys:
        to_unlock.append("first_quiz")
    if (
        stats["total_questions_answered"] >= 100
        and "hundred_questions" not in existing_keys
    ):
        to_unlock.append("hundred_questions")
    if stats["has_perfect_score"] and "perfect_score" not in existing_keys:
        to_unlock.append("perfect_score")
    if stats["current_streak"] >= 7 and "seven_day_streak" not in existing_keys:
        to_unlock.append("seven_day_streak")

    newly_unlocked = []
    for key in to_unlock:
        db.session.add(Achievement(user_id=user_id, key=key))
        newly_unlocked.append({"key": key, **ACHIEVEMENTS[key]})

    if newly_unlocked:
        db.session.commit()

    return newly_unlocked

def compute_teacher_stats(user_id):
    """Shared stats used by teacher achievement checks."""
    classes = Class.query.filter_by(teacher_id=user_id).all()
    class_ids = [c.id for c in classes]

    total_students = (
        ClassMembership.query.filter(ClassMembership.class_id.in_(class_ids))
        .distinct(ClassMembership.student_id)
        .count()
        if class_ids
        else 0
    )

    published_assignments_count = Quiz.query.filter_by(
        user_id=user_id, is_assignment=True, is_published=True
    ).count()

    return {
        "total_classes": len(classes),
        "total_students": total_students,
        "published_assignments_count": published_assignments_count,
    }


def check_and_unlock_teacher_achievements(user_id):
    """Same pattern as check_and_unlock_achievements, for teacher-specific
    milestones. Called from class-creation, class-join, and
    assignment-publish routes rather than quiz submission."""
    stats = compute_teacher_stats(user_id)
    existing_keys = {
        a.key for a in Achievement.query.filter_by(user_id=user_id).all()
    }

    to_unlock = []
    if stats["total_classes"] >= 1 and "first_class" not in existing_keys:
        to_unlock.append("first_class")
    if stats["total_students"] >= 10 and "ten_students" not in existing_keys:
        to_unlock.append("ten_students")
    if stats["total_students"] >= 50 and "fifty_students" not in existing_keys:
        to_unlock.append("fifty_students")
    if (
        stats["published_assignments_count"] >= 1
        and "first_assignment_published" not in existing_keys
    ):
        to_unlock.append("first_assignment_published")
    if (
        stats["published_assignments_count"] >= 5
        and "five_assignments_published" not in existing_keys
    ):
        to_unlock.append("five_assignments_published")

    newly_unlocked = []
    for key in to_unlock:
        db.session.add(Achievement(user_id=user_id, key=key))
        newly_unlocked.append({"key": key, **TEACHER_ACHIEVEMENTS[key]})

    if newly_unlocked:
        db.session.commit()

    return newly_unlocked

def get_achievements_for_user(user_id, is_teacher=False):
    """Returns every defined achievement (student or teacher set,
    depending on role) with unlocked status/date."""
    definitions = TEACHER_ACHIEVEMENTS if is_teacher else ACHIEVEMENTS
    unlocked = {
        a.key: a.unlocked_at
        for a in Achievement.query.filter_by(user_id=user_id).all()
    }
    return [
        {
            "key": key,
            "title": info["title"],
            "description": info["description"],
            "unlocked": key in unlocked,
            "unlocked_at": unlocked[key].isoformat() if key in unlocked else None,
        }
        for key, info in definitions.items()
    ]
