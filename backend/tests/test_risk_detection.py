from datetime import datetime, timedelta
from models import User, Document, Quiz, Attempt, StudySession
from risk_detection import assess_student_risk


def _make_user(db, username):
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


def _make_quiz(db, doc, teacher, num_questions=5):
    quiz = Quiz(
        document_id=doc.id, user_id=teacher.id, difficulty="easy",
        num_questions=num_questions, total_marks=num_questions,
        time_limit_minutes=10, is_assignment=True, is_published=True,
    )
    db.session.add(quiz)
    db.session.commit()
    return quiz


def _make_attempt(db, quiz, student, percentage, submitted_at):
    attempt = Attempt(
        quiz_id=quiz.id, user_id=student.id, max_score=quiz.total_marks,
        total_score=quiz.total_marks * percentage / 100,
        percentage=percentage, submitted_at=submitted_at,
    )
    db.session.add(attempt)
    db.session.commit()
    return attempt


def _make_study_session(db, student, doc, duration_seconds, started_at):
    session = StudySession(
        user_id=student.id, document_id=doc.id,
        duration_seconds=duration_seconds, started_at=started_at,
    )
    db.session.add(session)
    db.session.commit()
    return session


def test_healthy_student_is_not_flagged(app, db):
    """A student who submitted every assignment on time, recently, with
    no declining trend should NOT be flagged at all."""
    teacher = _make_user(db, "teacher1")
    student = _make_user(db, "student1")
    doc = _make_document(db, teacher)

    quizzes = [_make_quiz(db, doc, teacher) for _ in range(3)]
    now = datetime.utcnow()
    for i, quiz in enumerate(quizzes):
        _make_attempt(db, quiz, student, percentage=85, submitted_at=now - timedelta(days=i))

    _make_study_session(db, student, doc, duration_seconds=1800, started_at=now - timedelta(days=1))
    _make_study_session(db, student, doc, duration_seconds=1800, started_at=now)

    class_quiz_ids = [q.id for q in quizzes]
    risk = assess_student_risk(student.id, class_quiz_ids)

    assert risk is None


def test_never_active_student_is_flagged(app, db):
    """A student enrolled in a class with assignments, but who has never
    submitted anything and has no activity at all, should be flagged -
    missed everything AND never logged any activity."""
    teacher = _make_user(db, "teacher2")
    student = _make_user(db, "student2")
    doc = _make_document(db, teacher)
    quizzes = [_make_quiz(db, doc, teacher) for _ in range(3)]

    class_quiz_ids = [q.id for q in quizzes]
    risk = assess_student_risk(student.id, class_quiz_ids)

    assert risk is not None
    assert risk["level"] in ("medium", "high")
    assert any("Missed" in r for r in risk["reasons"])
    assert any("Never logged any activity" in r for r in risk["reasons"])


def test_missed_assignments_flagged(app, db):
    """A student who only completed 1 of 5 assignments should be flagged
    for missed assignments, even if their one submitted score was fine."""
    teacher = _make_user(db, "teacher3")
    student = _make_user(db, "student3")
    doc = _make_document(db, teacher)
    quizzes = [_make_quiz(db, doc, teacher) for _ in range(5)]
    now = datetime.utcnow()

    _make_attempt(db, quizzes[0], student, percentage=90, submitted_at=now - timedelta(days=1))

    class_quiz_ids = [q.id for q in quizzes]
    risk = assess_student_risk(student.id, class_quiz_ids)

    assert risk is not None
    assert any("Missed 4 assignments" in r for r in risk["reasons"])


def test_low_average_score_flagged(app, db):
    """A student consistently scoring below the low-score threshold should
    be flagged even with no missed assignments and recent activity."""
    teacher = _make_user(db, "teacher4")
    student = _make_user(db, "student4")
    doc = _make_document(db, teacher)
    quizzes = [_make_quiz(db, doc, teacher) for _ in range(3)]
    now = datetime.utcnow()

    for i, quiz in enumerate(quizzes):
        _make_attempt(db, quiz, student, percentage=35, submitted_at=now - timedelta(days=i))

    class_quiz_ids = [q.id for q in quizzes]
    risk = assess_student_risk(student.id, class_quiz_ids)

    assert risk is not None
    assert risk["overall_average"] == 35
    assert any("Average score is 35.0%" in r for r in risk["reasons"])


def test_declining_trend_flagged(app, db):
    """A student whose scores dropped significantly in their more recent
    attempts (vs their earlier ones) should be flagged for the trend,
    even though their overall average might look fine."""
    teacher = _make_user(db, "teacher5")
    student = _make_user(db, "student5")
    doc = _make_document(db, teacher)
    quizzes = [_make_quiz(db, doc, teacher) for _ in range(6)]
    now = datetime.utcnow()

    # Earlier attempts: strong. Recent attempts: much weaker.
    scores = [90, 88, 85, 40, 35, 30]
    for i, (quiz, score) in enumerate(zip(quizzes, scores)):
        _make_attempt(db, quiz, student, percentage=score, submitted_at=now - timedelta(days=6 - i))

    class_quiz_ids = [q.id for q in quizzes]
    risk = assess_student_risk(student.id, class_quiz_ids)

    assert risk is not None
    assert any("dropped" in r for r in risk["reasons"])


def test_inactive_student_flagged(app, db):
    """A student with a decent history but no activity in a long time
    should be flagged for inactivity, regardless of past scores."""
    teacher = _make_user(db, "teacher6")
    student = _make_user(db, "student6")
    doc = _make_document(db, teacher)
    quizzes = [_make_quiz(db, doc, teacher) for _ in range(2)]
    long_ago = datetime.utcnow() - timedelta(days=20)

    for quiz in quizzes:
        _make_attempt(db, quiz, student, percentage=80, submitted_at=long_ago)

    class_quiz_ids = [q.id for q in quizzes]
    risk = assess_student_risk(student.id, class_quiz_ids)

    assert risk is not None
    assert any("No activity in" in r for r in risk["reasons"])


def test_no_assignments_in_class_returns_none(app, db):
    """If the class has no tagged assignments at all, there's nothing to
    assess risk against - should return None, not crash on empty data."""
    teacher = _make_user(db, "teacher7")
    student = _make_user(db, "student7")

    risk = assess_student_risk(student.id, class_quiz_ids=[])

    assert risk is None