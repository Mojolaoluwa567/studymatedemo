"""
Functions that run INSIDE the RQ worker process (a separate `python3
worker.py` process, not the Flask web process). Each job function needs
its own Flask app context to touch the database, since it's not running
inside a normal request.
"""
import logging


def generate_quiz_job(document_id, difficulty, format_mode, user_id, is_assignment, title):
    """
    The actual Gemini quiz generation call, run in the background worker.
    Returns a dict the frontend can use to build the quiz result, or
    raises (RQ records the exception, get_job_status surfaces it).
    """
    from app import app, db
    from models import Document, Quiz, Question
    from quiz_generator import generate_quiz_questions
    from rag import get_prompt_text_for_document

    with app.app_context():
        document = Document.query.filter_by(id=document_id, user_id=user_id).first()
        if not document:
            raise ValueError("Document not found")

        text_for_prompt = get_prompt_text_for_document(
            document, f"{difficulty} difficulty quiz covering the whole document"
        )

        plan, generated_questions = generate_quiz_questions(
            text_for_prompt, difficulty, format_mode
        )

        quiz = Quiz(
            document_id=document.id,
            user_id=user_id,
            difficulty=difficulty,
            num_questions=len(generated_questions),
            total_marks=plan["total_marks"],
            time_limit_minutes=plan["time_limit_minutes"],
            is_assignment=is_assignment,
            is_published=not is_assignment,  # assignments start as drafts, personal quizzes are immediately usable
            title=title,
        )
        db.session.add(quiz)
        db.session.flush()

        for i, q in enumerate(generated_questions):
            db.session.add(Question(
                quiz_id=quiz.id,
                order_index=i,
                type=q.get("type", "mcq"),
                question_text=q.get("question", ""),
                options=q.get("options") if q.get("type") == "mcq" else None,
                correct_answer=str(q.get("correct_answer", "")),
                marks=int(q.get("marks", 1)),
                topic=q.get("topic"),
            ))

        db.session.commit()
        return {"quiz_id": quiz.id}


def send_email_job(fn_name, args):
    """
    Runs any send_*_email function from email_utils in the background
    worker process. Doesn't need Flask app context - these functions
    only use os.environ and smtplib, no database access.
    """
    import email_utils
    getattr(email_utils, fn_name)(*args)