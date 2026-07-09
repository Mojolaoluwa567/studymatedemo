from datetime import datetime
from models import User, Document, Quiz, Attempt
from achievements import compute_stats, check_and_unlock_achievements


def _make_user(db, username="tester"):
    user = User(username=username, email=f"{username}@example.com", password="hashed")
    db.session.add(user)
    db.session.commit()
    return user


def _make_document(db, user):
    doc = Document(
        user_id=user.id, title="Doc", filename="doc.pdf",
        text_content="text", source_type="pdf",
    )
    db.session.add(doc)
    db.session.commit()
    return doc


def _make_quiz(db, doc, user, num_questions=5):
    quiz = Quiz(
        document_id=doc.id, user_id=user.id, difficulty="easy",
        num_questions=num_questions, total_marks=num_questions,
        time_limit_minutes=10,
    )
    db.session.add(quiz)
    db.session.commit()
    return quiz


def _make_attempt(db, quiz, user, percentage):
    attempt = Attempt(
        quiz_id=quiz.id, user_id=user.id, max_score=quiz.total_marks,
        total_score=quiz.total_marks * percentage / 100,
        percentage=percentage, submitted_at=datetime.utcnow(),
    )
    db.session.add(attempt)
    db.session.commit()
    return attempt


def test_compute_stats_no_attempts(app, db):
    user = _make_user(db)
    stats = compute_stats(user.id)
    assert stats["total_quizzes"] == 0
    assert stats["average_score"] == 0
    assert stats["has_perfect_score"] is False


def test_compute_stats_with_attempts(app, db):
    user = _make_user(db)
    doc = _make_document(db, user)
    quiz = _make_quiz(db, doc, user, num_questions=5)
    _make_attempt(db, quiz, user, percentage=80)
    _make_attempt(db, quiz, user, percentage=100)

    stats = compute_stats(user.id)
    assert stats["total_quizzes"] == 2
    assert stats["total_questions_answered"] == 10
    assert stats["average_score"] == 90.0
    assert stats["has_perfect_score"] is True


def test_first_quiz_achievement_unlocks_once(app, db):
    user = _make_user(db)
    doc = _make_document(db, user)
    quiz = _make_quiz(db, doc, user)
    _make_attempt(db, quiz, user, percentage=50)

    unlocked = check_and_unlock_achievements(user.id)
    assert any(a["key"] == "first_quiz" for a in unlocked)

    unlocked_again = check_and_unlock_achievements(user.id)
    assert not any(a["key"] == "first_quiz" for a in unlocked_again)


def test_perfect_score_achievement(app, db):
    user = _make_user(db)
    doc = _make_document(db, user)
    quiz = _make_quiz(db, doc, user)
    _make_attempt(db, quiz, user, percentage=100)

    unlocked = check_and_unlock_achievements(user.id)
    assert any(a["key"] == "perfect_score" for a in unlocked)