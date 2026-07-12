from datetime import datetime
from extensions import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # "student" | "teacher" - chosen at signup, controls which dashboard
    # and capabilities the frontend shows. Both roles use the same User
    # table and the same login/auth flow.
    role = db.Column(db.String(20), nullable=False, default="student")

    # Separate privilege layer, not a 3rd role value - an admin is still
    # also a student or teacher underneath (DashboardRouter is untouched;
    # admin access is purely additive on top). Not self-service: there's
    # no signup option for this, it's set directly in the database.
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    # Google OAuth — stores the Google sub (unique user ID) for accounts
    # that signed up or linked via Google. Null for password-only accounts.
    google_id = db.Column(db.String(128), nullable=True, unique=True)

    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

    documents = db.relationship(
        "Document", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    attempts = db.relationship(
        "Attempt", backref="user", lazy=True, cascade="all, delete-orphan"
    )


class Document(db.Model):
    """An uploaded course PDF, with its extracted text cached for quiz generation."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    title = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    text_content = db.Column(db.Text, nullable=False)
    page_count = db.Column(db.Integer, default=0)
    # Raw PDF bytes stored for in-browser PDF viewer in the Read tab.
    # Only populated for PDF uploads; null for text/URL/YouTube/audio sources.
    pdf_data = db.Column(db.LargeBinary, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # "pdf" | "docx" | "text" | "url" - lets the frontend show the right
    # icon/label without guessing from the filename.
    source_type = db.Column(db.String(20), nullable=False, default="pdf")
    # Only set when source_type == "url" - the original page fetched.
    source_url = db.Column(db.String(2048), nullable=True)

    # Cached AI study aids - generated lazily on first request, then reused.
    summary = db.Column(db.Text, nullable=True)
    key_concepts = db.Column(db.JSON, nullable=True)
    flashcards = db.Column(db.JSON, nullable=True)
    explainer_html = db.Column(db.Text, nullable=True)

    quizzes = db.relationship(
        "Quiz", backref="document", lazy=True, cascade="all, delete-orphan"
    )
    study_sessions = db.relationship(
        "StudySession", backref="document", lazy=True, cascade="all, delete-orphan"
    )


class StudySession(db.Model):
    """A timed reading/study session against a document, used for long-term
    performance analytics (study time vs quiz score)."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    document_id = db.Column(
        db.Integer, db.ForeignKey("document.id"), nullable=False, index=True
    )
    duration_seconds = db.Column(db.Integer, nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)


DIFFICULTY_LEVELS = ("easy", "hard", "difficult")
QUESTION_TYPES = ("mcq", "theory")


class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(
        db.Integer, db.ForeignKey("document.id"), nullable=False, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    difficulty = db.Column(db.String(20), nullable=False)
    num_questions = db.Column(db.Integer, nullable=False)
    total_marks = db.Column(db.Integer, nullable=False)
    time_limit_minutes = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Set when a teacher creates this quiz to assign to students (as
    # opposed to a student's personal self-study quiz). Assignment quizzes
    # get a short shareable join_code; personal quizzes leave both null.
    is_assignment = db.Column(db.Boolean, nullable=False, default=False)
    join_code = db.Column(db.String(10), unique=True, nullable=True, index=True)
    title = db.Column(db.String(255), nullable=True)  # assignment display name

    # Draft/review/publish workflow for assignments: a teacher generates
    # questions into a draft (is_published=False), can review/edit/delete
    # individual questions, then publishes. The join code only works for
    # students once published. Defaults to True so personal (non-assignment)
    # quizzes and any pre-existing assignment data behave exactly as before.
    is_published = db.Column(db.Boolean, nullable=False, default=True)

    questions = db.relationship(
        "Question",
        backref="quiz",
        lazy=True,
        order_by="Question.order_index",
        cascade="all, delete-orphan",
    )
    attempts = db.relationship(
        "Attempt", backref="quiz", lazy=True, cascade="all, delete-orphan"
    )


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(
        db.Integer, db.ForeignKey("quiz.id"), nullable=False, index=True
    )
    order_index = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'mcq' | 'theory'
    question_text = db.Column(db.Text, nullable=False)
    # For MCQ: JSON-encoded {"A": "...", "B": "...", "C": "...", "D": "..."}
    options = db.Column(db.JSON, nullable=True)
    # For MCQ: the correct option key (e.g. "B")
    # For theory: a model answer / marking points used for grading reference
    correct_answer = db.Column(db.Text, nullable=False)
    marks = db.Column(db.Integer, nullable=False)
    # Short topic/concept label the AI assigns at generation time (e.g.
    # "Deadlocks", "CPU Scheduling") - used to aggregate per-topic mastery
    # across attempts. Nullable since older questions predate this field.
    topic = db.Column(db.String(100), nullable=True)


class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(
        db.Integer, db.ForeignKey("quiz.id"), nullable=False, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    # For quizzes with both MCQ and theory (Stage 3 — Difficult), the
    # student submits MCQ first, then theory. mcq_submitted_at is set when
    # the MCQ phase is completed; submitted_at is set when the full attempt
    # (including theory) is complete. For MCQ-only quizzes, mcq_submitted_at
    # stays null and submitted_at is set in a single step.
    mcq_submitted_at = db.Column(db.DateTime, nullable=True)
    mcq_score = db.Column(db.Float, nullable=True)
    submitted_at = db.Column(db.DateTime, nullable=True)
    study_time_seconds = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Float, nullable=True)
    max_score = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=True)

    answers = db.relationship(
        "Answer", backref="attempt", lazy=True, cascade="all, delete-orphan"
    )


class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    key = db.Column(db.String(50), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "key", name="uq_user_achievement"),)


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(
        db.Integer, db.ForeignKey("attempt.id"), nullable=False, index=True
    )
    question_id = db.Column(
        db.Integer, db.ForeignKey("question.id"), nullable=False, index=True
    )
    user_answer = db.Column(db.Text, nullable=True)
    score_awarded = db.Column(db.Float, default=0)
    is_correct = db.Column(db.Boolean, nullable=True)  # MCQ only
    feedback = db.Column(db.Text, nullable=True)  # theory only
    explanation = db.Column(db.Text, nullable=True)  # "explain my mistakes"

    question = db.relationship("Question")


class Class(db.Model):
    """
    Lightweight teacher-created class/cohort. Students join once with a
    class code and then automatically see all published assignments tagged
    to that class. Teachers can tag any assignment to one of their classes.
    """
    __tablename__ = "class"
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    join_code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teacher = db.relationship("User", backref="taught_classes", foreign_keys=[teacher_id])
    memberships = db.relationship("ClassMembership", backref="class_", lazy=True, cascade="all, delete-orphan")


class ClassMembership(db.Model):
    """Student membership in a class - created when a student joins via code."""
    __tablename__ = "class_membership"
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("class_id", "student_id", name="uq_class_student"),
    )


class ClassAssignment(db.Model):
    """Links a published quiz/assignment to a class."""
    __tablename__ = "class_assignment"
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class.id"), nullable=False, index=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False, index=True)

    __table_args__ = (
        db.UniqueConstraint("class_id", "quiz_id", name="uq_class_quiz"),
    )

class Announcement(db.Model):
    """One-way broadcast from a teacher to every member of a class."""
    __tablename__ = "announcement"
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class.id"), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class_ = db.relationship("Class", backref=db.backref("announcements", cascade="all, delete-orphan")) 

class DocumentChunk(db.Model):
    """
    A chunk of a document's text with its embedding vector, used for RAG
    retrieval so quiz/study-aid generation can pull the MOST RELEVANT
    portion of a long document instead of always using the first ~18k
    characters (the old truncation approach).

    Embedding storage: stored as JSON (a list of floats) rather than a
    native pgvector column, so the SAME model works against both SQLite
    (local dev) and Postgres (production) without maintaining two schemas.
    Similarity search is done in Python (see rag.py) rather than pushed
    down as a SQL vector operator - slower than native pgvector cosine
    distance at large scale, but for a single document's chunks (dozens,
    not millions) the difference is invisible, and it keeps local dev
    working without requiring Postgres + the pgvector extension.
    """
    __tablename__ = "document_chunk"
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(
        db.Integer, db.ForeignKey("document.id"), nullable=False, index=True
    )
    chunk_index = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.JSON, nullable=True)  # list[float], null until embedded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    document = db.relationship("Document", backref=db.backref(
        "chunks", lazy=True, cascade="all, delete-orphan"
    ))
