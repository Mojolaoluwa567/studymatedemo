"""
Rules-based risk detection for teachers: flags students who are likely to
fail, disengaging, or need intervention, using signals already present in
the data (Attempt, StudySession) - no extra tracking tables, no AI call
required for the core detection. An optional one-line AI-written summary
can be layered on top per flagged student (see get_ai_risk_note below),
kept separate from the scoring itself so the actual risk determination
stays transparent and auditable, not hidden inside an LLM call.
"""

from datetime import datetime

from models import Attempt, StudySession
from quiz_generator import get_client, MODEL


# Tuned to flag real, actionable concern rather than every minor dip -
# a teacher checking this page should see a short, meaningful list, not
# every student who had one off day.
INACTIVITY_DAYS_THRESHOLD = 10
DECLINING_TREND_THRESHOLD = 15  # percentage-point drop, recent vs earlier
LOW_SCORE_THRESHOLD = 50
STUDY_TIME_DROP_THRESHOLD = 50  # percent drop, recent vs earlier


def _student_signals(student_id, class_quiz_ids):
    """Gathers the raw signals used to score one student's risk level,
    scoped to attempts on this class's tagged assignments only - not a
    student's unrelated personal quizzes."""
    attempts = (
        Attempt.query.filter(
            Attempt.user_id == student_id,
            Attempt.quiz_id.in_(class_quiz_ids),
            Attempt.submitted_at.isnot(None),
        )
        .order_by(Attempt.submitted_at.asc())
        .all()
    )

    study_sessions = (
        StudySession.query.filter_by(user_id=student_id)
        .order_by(StudySession.started_at.asc())
        .all()
    )

    last_activity = None
    if attempts:
        last_activity = attempts[-1].submitted_at
    if study_sessions:
        last_study = study_sessions[-1].started_at
        if not last_activity or last_study > last_activity:
            last_activity = last_study

    days_inactive = (
        (datetime.utcnow() - last_activity).days if last_activity else None
    )

    missed_count = len(class_quiz_ids) - len({a.quiz_id for a in attempts})

    # Recent vs earlier average, to detect a declining trend rather than
    # just a flat low average (a student improving from 30% to 60% isn't
    # "at risk" even though some individual scores were low).
    trend_drop = 0
    if len(attempts) >= 4:
        midpoint = len(attempts) // 2
        earlier_avg = sum(a.percentage for a in attempts[:midpoint]) / midpoint
        recent_avg = sum(a.percentage for a in attempts[midpoint:]) / (
            len(attempts) - midpoint
        )
        trend_drop = earlier_avg - recent_avg

    overall_avg = (
        round(sum(a.percentage for a in attempts) / len(attempts), 1)
        if attempts
        else None
    )

    study_time_drop_pct = 0
    if len(study_sessions) >= 4:
        midpoint = len(study_sessions) // 2
        earlier_total = sum(s.duration_seconds for s in study_sessions[:midpoint])
        recent_total = sum(s.duration_seconds for s in study_sessions[midpoint:])
        if earlier_total > 0:
            study_time_drop_pct = round(
                ((earlier_total - recent_total) / earlier_total) * 100, 1
            )

    return {
        "attempts_count": len(attempts),
        "missed_count": max(0, missed_count),
        "overall_average": overall_avg,
        "trend_drop": round(trend_drop, 1),
        "days_inactive": days_inactive,
        "study_time_drop_pct": study_time_drop_pct,
    }


def assess_student_risk(student_id, class_quiz_ids):
    """
    Returns None if the student shows no concerning signals, or a dict
    with a risk score (0-100), level, and the specific reasons that
    triggered it - so a teacher sees WHY, not just a number.
    """
    if not class_quiz_ids:
        # Nothing has been assigned to this class yet - there's no basis
        # to assess risk against, so don't flag anyone.
        return None

    signals = _student_signals(student_id, class_quiz_ids)
    reasons = []
    score = 0

    if signals["missed_count"] >= 3:
        score += 30
        reasons.append(f"Missed {signals['missed_count']} assignments")
    elif signals["missed_count"] >= 1:
        score += 12
        reasons.append(f"Missed {signals['missed_count']} assignment(s)")

    if signals["overall_average"] is not None and signals["overall_average"] < LOW_SCORE_THRESHOLD:
        score += 25
        reasons.append(f"Average score is {signals['overall_average']}%")

    if signals["trend_drop"] >= DECLINING_TREND_THRESHOLD:
        score += 25
        reasons.append(
            f"Scores dropped {signals['trend_drop']} points recently"
        )

    if signals["days_inactive"] is not None and signals["days_inactive"] >= INACTIVITY_DAYS_THRESHOLD:
        score += 20
        reasons.append(f"No activity in {signals['days_inactive']} days")
    elif signals["days_inactive"] is None:
        score += 15
        reasons.append("Never logged any activity")

    if signals["study_time_drop_pct"] >= STUDY_TIME_DROP_THRESHOLD:
        score += 15
        reasons.append(
            f"Study time dropped {signals['study_time_drop_pct']}%"
        )

    if not reasons:
        return None

    score = min(100, score)
    level = "high" if score >= 60 else "medium" if score >= 30 else "low"

    return {
        "student_id": student_id,
        "risk_score": score,
        "level": level,
        "reasons": reasons,
        "overall_average": signals["overall_average"],
    }


def get_ai_risk_note(student_username, reasons):
    """Optional one-line AI-written intervention suggestion for a
    flagged student, layered on top of the rules-based reasons above.
    Kept separate and best-effort - if this call fails, the risk
    flag itself (from assess_student_risk) is still fully usable
    without it."""
    prompt = (
        f"A student named {student_username} has been flagged with these "
        f"concerns: {'; '.join(reasons)}. In ONE short sentence (under 25 "
        "words), suggest a specific, actionable next step their teacher "
        "could take. Respond with ONLY that sentence, no preamble."
    )
    response = get_client().models.generate_content(model=MODEL, contents=prompt)
    return response.text.strip()