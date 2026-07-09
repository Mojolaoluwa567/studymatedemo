import os
import logging
import secrets
from functools import wraps
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

import click
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from extensions import db, bcrypt, jwt
from models import (
    User,
    Document,
    StudySession,
    Quiz,
    Question,
    Attempt,
    Answer,
    Class,
    ClassMembership,
    ClassAssignment,
)
from content_ingestion import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_plain_text,
    extract_text_from_url,
    extract_text_from_youtube,
    extract_text_from_audio,
    truncate_for_prompt,
)
from rag import get_prompt_text_for_document
from quiz_generator import (
    generate_quiz_questions,
    generate_lecturer_style_quiz_questions,
    generate_weak_spots_quiz,
    get_quiz_plan,
    EASY_MODES,
    HARD_MODES,
    DIFFICULT_MODES,
    PATTERN_TRAINER_MODES,
    transcribe_audio,
)
from grading import grade_mcq, grade_theory_batch, explain_mistakes_batch
from email_utils import send_email, send_welcome_email, send_password_reset_email, send_login_notification_email, send_achievement_email
from study_aids import generate_summary, generate_key_concepts, generate_flashcards, generate_explainer
from achievements import (
    compute_stats,
    check_and_unlock_achievements,
    get_achievements_for_user,
)
from admin import (
    get_admin_overview,
    get_admin_users,
    get_admin_user_detail,
    get_admin_content,
    get_admin_usage,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me-32chars")
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me-32chars")

# Some hosts (Railway, Render, Heroku) hand out DATABASE_URL with the
# legacy "postgres://" scheme, which SQLAlchemy 1.4+/2.x no longer
# recognizes - it needs "postgresql://". Normalize it here so the same
# .env style works everywhere without the host needing to change anything.
_database_url = os.environ.get(
    "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"
)
if _database_url.startswith("postgres://"):
    _database_url = _database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = _database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB upload limit

# Access tokens expire so a stolen/leaked token doesn't work forever.
# Refresh tokens last longer and are used to silently get a new access
# token without forcing the user to log in again.
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
app.config["JWT_TOKEN_LOCATION"] = ["headers", "query_string"]
app.config["JWT_QUERY_STRING_NAME"] = "token"

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")

db.init_app(app)
bcrypt.init_app(app)
jwt.init_app(app)
migrate = Migrate(app, db)
CORS(app, supports_credentials=True, origins=[FRONTEND_ORIGIN])

# Rate limiting protects the shared Gemini free-tier quota from being
# exhausted by one user (or a bug) hammering the AI endpoints. Keyed by IP
# address by default; storage is in-memory, which is fine for a single
# server instance (the typical setup at this scale).
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="memory://",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@app.before_request
def _log_request_start():
    request.start_time = datetime.utcnow()


@app.after_request
def _log_request_end(response):
    try:
        duration_ms = (datetime.utcnow() - request.start_time).total_seconds() * 1000
        user_id = None
        try:
            from flask_jwt_extended import get_jwt_identity
            user_id = get_jwt_identity()
        except Exception:
            pass
        logging.info(
            f"{request.method} {request.path} -> {response.status_code} "
            f"({duration_ms:.0f}ms) user={user_id or 'anon'}"
        )
    except Exception:
        pass
    return response

# Schema is managed exclusively through Flask-Migrate from here on - see
# migrations/. db.create_all() used to run here on every boot, which
# silently kept local dev in sync but meant "flask db migrate" could never
# detect real changes (the schema was always already applied before Alembic
# looked at it). Local setup is now: `flask db upgrade` once after cloning,
# same as production.


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _validate_password_strength(password):
    """Returns a list of unmet requirements, empty if password is strong."""
    errors = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not any(c.isupper() for c in password):
        errors.append("one uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("one lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("one number")
    if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password):
        errors.append("one special character")
    return errors

@app.route("/auth/google", methods=["POST"])
@limiter.limit("20 per hour")
def google_auth():
    """
    Verifies a Google ID token sent from the frontend (obtained via the
    Google Identity Services JS SDK). If the Google account email matches
    an existing user, logs them in. If not, creates a new account
    automatically with the Google profile data.

    The frontend sends: { credential: "<google_id_token>", role: "student"|"teacher" }
    role is only used when creating a new account; ignored for existing ones.
    """
    data = request.get_json()
    credential = data.get("credential")
    role = data.get("role", "student")

    if not credential:
        return jsonify(error="Google credential is required"), 400

    google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not google_client_id:
        return jsonify(error="Google OAuth is not configured on this server"), 503

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        id_info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            google_client_id,
        )
    except ValueError as e:
        logging.warning(f"Google token verification failed: {e}")
        return jsonify(error="Invalid or expired Google credential"), 401
    except Exception as e:
        logging.error(f"Google auth error: {e}")
        return jsonify(error="Google authentication failed"), 502

    google_id = id_info["sub"]
    email = id_info.get("email", "").lower()
    name = id_info.get("name", "")

    if not email:
        return jsonify(error="Google account has no email address"), 400

    # Check if an account is already linked to this Google ID
    user = User.query.filter_by(google_id=google_id).first()

    if not user:
        # Check if an account exists with the same email (password signup)
        user = User.query.filter_by(email=email).first()

        if user:
            # Link the existing account to Google
            user.google_id = google_id
            db.session.commit()

        else:
            # Brand new account — derive a username from the Google name
            base_username = "".join(
                c for c in name.lower().replace(" ", "_")
                if c.isalnum() or c == "_"
            )[:20] or "user"

            username = base_username
            suffix = 1

            while User.query.filter_by(username=username).first():
                username = f"{base_username}{suffix}"
                suffix += 1

            if role not in ("student", "teacher"):
                role = "student"

            # Google accounts don't have a local password
            unusable_password = bcrypt.generate_password_hash(
                secrets.token_hex(32)
            ).decode("utf-8")

            user = User(
                username=username,
                email=email,
                password=unusable_password,
                role=role,
                google_id=google_id,
            )

            db.session.add(user)
            db.session.commit()

            try:
                send_welcome_email(email, username, role)
            except Exception as e:
                logging.warning(
                    f"Welcome email failed for Google signup {username}: {e}"
                )

    access_token = create_access_token(identity=str(user.id))

    try:
        login_time_str = datetime.utcnow().strftime("%b %d, %Y at %H:%M UTC")
        import threading
        threading.Thread(
            target=send_login_notification_email,
            args=(user.email, user.username, login_time_str),
            daemon=True,
        ).start()
    except Exception as e:
        logging.warning(f"Login notification email failed for Google login {user.username}: {e}")

    return jsonify(
        access_token=access_token,
        username=user.username,
        role=user.role,
    )


@app.route("/health", methods=["GET"])
def health_check():
    """
    Lightweight endpoint for uptime monitoring / keep-alive pings (e.g.
    cron-job.org hitting this every 10 min to prevent Render's free tier
    from spinning the service down). No auth, no DB query - just confirms
    the process is alive and responding.
    """
    return jsonify(status="ok"), 200


@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "student")

    if not username or not email or not password:
        return jsonify(error="Username, email and password are required"), 400

    if role not in ("student", "teacher"):
        role = "student"

    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify(error="Please enter a valid email address"), 400

    pw_errors = _validate_password_strength(password)
    if pw_errors:
        return jsonify(
            error=f"Password must contain {', '.join(pw_errors)}."
        ), 400

    if User.query.filter_by(username=username).first():
        return jsonify(error="Username already exists"), 409

    if User.query.filter_by(email=email.lower()).first():
        return jsonify(error="An account with this email already exists"), 409

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(
        username=username, email=email.lower(), password=hashed_password, role=role
    )
    db.session.add(user)
    db.session.commit()

    # Fire-and-forget welcome email - don't let email failure block signup
    try:
        send_welcome_email(email.lower(), username, role)
    except Exception as e:
        logging.warning(f"Welcome email failed for {username}: {e}")

    access_token = create_access_token(identity=str(user.id))

    # Treat signup as an implicit first login - send the same
    # sign-in notification that /login and /auth/google send.
    try:
        login_time_str = datetime.utcnow().strftime("%b %d, %Y at %H:%M UTC")
        import threading
        threading.Thread(
            target=send_login_notification_email,
            args=(user.email, user.username, login_time_str),
            daemon=True,
        ).start()
    except Exception as e:
        logging.warning(f"Login notification email failed for new signup {username}: {e}")

    return jsonify(
        message="User created successfully",
        access_token=access_token,
        username=user.username,
        role=user.role,
    )


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    identifier = (data.get("username") or "").strip()
    password = data.get("password")

    if not identifier or not password:
        return jsonify(error="Username/email and password are required"), 400

    if "@" in identifier:
        user = User.query.filter_by(email=identifier.lower()).first()
    else:
        user = User.query.filter_by(username=identifier).first()

    if user and bcrypt.check_password_hash(user.password, password):
        access_token = create_access_token(identity=str(user.id))

        try:
            login_time_str = datetime.utcnow().strftime("%b %d, %Y at %H:%M UTC")
            import threading
            threading.Thread(
                target=send_login_notification_email,
                args=(user.email, user.username, login_time_str),
                daemon=True,
            ).start()
        except Exception as e:
            logging.warning(f"Login notification email failed for {user.username}: {e}")

        return jsonify(
            message="Login successful",
            access_token=access_token,
            username=user.username,
            role=user.role,
        )
    return jsonify(error="Invalid credentials"), 401


@app.route("/logout", methods=["POST"])
def logout():
    return jsonify(message="Logged out")


@app.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify(error="User not found"), 404
    return jsonify(
        username=user.username,
        email=user.email,
        role=user.role,
        is_admin=user.is_admin,
        member_since=user.created_at.isoformat() if user.created_at else None,
    )


@app.route("/profile/change-password", methods=["POST"])
@jwt_required()
def change_password():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify(error="User not found"), 404

    data = request.get_json()
    current_password = data.get("current_password")
    new_password = data.get("new_password")

    if not current_password or not new_password:
        return jsonify(error="Current and new password are required"), 400

    if not bcrypt.check_password_hash(user.password, current_password):
        return jsonify(error="Current password is incorrect"), 401

    pw_errors = _validate_password_strength(new_password)
    if pw_errors:
        return jsonify(error=f"Password must contain {', '.join(pw_errors)}."), 400

    user.password = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.session.commit()
    return jsonify(message="Password updated successfully")


@app.route("/profile/stats", methods=["GET"])
@jwt_required()
def profile_stats():
    user_id = int(get_jwt_identity())

    total_documents = Document.query.filter_by(user_id=user_id).count()
    stats = compute_stats(user_id)

    return jsonify(
        total_documents=total_documents,
        total_quizzes=stats["total_quizzes"],
        total_questions_answered=stats["total_questions_answered"],
        average_score=stats["average_score"],
        current_streak=stats["current_streak"],
    )


@app.route("/achievements", methods=["GET"])
@jwt_required()
def list_achievements():
    user_id = int(get_jwt_identity())
    return jsonify(achievements=get_achievements_for_user(user_id))


@app.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per hour")
def forgot_password():
    data = request.get_json()
    email = (data.get("email") or "").lower().strip()

    if not email:
        return jsonify(error="Email is required"), 400

    user = User.query.filter_by(email=email).first()

    # Always respond the same way whether or not the email exists, so an
    # attacker can't use this endpoint to discover registered emails.
    generic_message = (
        "If an account with that email exists, a password reset link "
        "has been sent."
    )

    if not user:
        return jsonify(message=generic_message)

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.session.commit()

    frontend_url = FRONTEND_ORIGIN.rstrip("/")
    reset_link = f"{frontend_url}/reset-password?token={token}"

    sent = send_password_reset_email(
        to_address=user.email,
        username=user.username,
        reset_link=reset_link,
    )

    if sent:
        return jsonify(message=generic_message)

    # Dev mode: no SMTP configured, so return the link directly so the
    # flow is still testable end-to-end.
    return jsonify(
        message=generic_message,
        dev_mode=True,
        reset_link=reset_link,
    )


@app.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    token = data.get("token")
    new_password = data.get("new_password")

    if not token or not new_password:
        return jsonify(error="Token and new password are required"), 400

    pw_errors = _validate_password_strength(new_password)
    if pw_errors:
        return jsonify(error=f"Password must contain {', '.join(pw_errors)}."), 400

    user = User.query.filter_by(reset_token=token).first()
    if (
        not user
        or not user.reset_token_expires
        or user.reset_token_expires < datetime.utcnow()
    ):
        return jsonify(error="This reset link is invalid or has expired"), 400

    user.password = bcrypt.generate_password_hash(new_password).decode("utf-8")
    user.reset_token = None
    user.reset_token_expires = None
    db.session.commit()

    return jsonify(message="Password has been reset successfully")


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {".pdf": "pdf", ".docx": "docx"}


@app.route("/documents", methods=["POST"])
@jwt_required()
def upload_document():
    """
    Handles file-based uploads: PDF and Word (.docx).
    For pasted text or a web page URL, see /documents/from-text and
    /documents/from-url below - those aren't file uploads so they don't
    fit multipart/form-data the same way.
    """
    if "file" not in request.files:
        return jsonify(error="No file uploaded (expected form field 'file')"), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify(error="No file selected"), 400

    ext = os.path.splitext(file.filename.lower())[1]
    source_type = ALLOWED_EXTENSIONS.get(ext)
    if not source_type:
        return jsonify(
            error="Unsupported file type. Upload a PDF or Word (.docx) document."
        ), 400

    try:
        if source_type == "pdf":
            file_bytes = file.read()
            import io
            text_content, page_count = extract_text_from_pdf(io.BytesIO(file_bytes))
        else:  # docx
            file_bytes = None
            text_content, page_count = extract_text_from_docx(file.stream)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        logging.error(f"{source_type} extraction failed: {e}")
        return jsonify(error=f"Could not read this {source_type} file"), 400

    title = (request.form.get("title") or "").strip()
    if not title:
        return jsonify(error="Please give this document a title so you can find it easily."), 400

    document = Document(
        user_id=int(get_jwt_identity()),
        title=title,
        filename=file.filename,
        text_content=text_content,
        page_count=page_count,
        source_type=source_type,
        pdf_data=file_bytes if source_type == "pdf" else None,
    )
    db.session.add(document)
    db.session.commit()

    # RAG: chunk + embed long documents so generation can retrieve the
    # most relevant portion instead of always truncating to the first
    # ~18k characters. Short documents skip this (see should_chunk).
    try:
        from rag import embed_document_chunks
        embed_document_chunks(document)
    except Exception as e:
        logging.warning(f"Chunk embedding failed for document {document.id}: {e}")

    return jsonify(
        id=document.id,
        title=document.title,
        page_count=document.page_count,
        source_type=document.source_type,
        uploaded_at=document.uploaded_at.isoformat(),
    )


@app.route("/documents/bulk", methods=["POST"])
@limiter.limit("20 per hour")
@jwt_required()
def bulk_upload_documents():
    """
    Upload multiple files at once. Accepts multiple 'files' fields in a
    single multipart request. Processes each independently — one bad file
    doesn't fail the whole batch. Returns per-file results so the frontend
    can show which succeeded and which failed.
    """
    files = request.files.getlist("files")
    if not files:
        return jsonify(error="No files uploaded (expected form field 'files')"), 400
    if len(files) > 20:
        return jsonify(error="Max 20 files per batch"), 400

    user_id = int(get_jwt_identity())
    results = []

    for file in files:
        if not file.filename:
            results.append({"filename": "", "success": False, "error": "No filename"})
            continue

        ext = os.path.splitext(file.filename.lower())[1]
        source_type = ALLOWED_EXTENSIONS.get(ext)
        if not source_type:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": "Unsupported file type (PDF or Word only)",
            })
            continue

        try:
            if source_type == "pdf":
                file_bytes = file.read()
                import io
                text_content, page_count = extract_text_from_pdf(io.BytesIO(file_bytes))
            else:
                file_bytes = None
                text_content, page_count = extract_text_from_docx(file.stream)

            title = file.filename.rsplit(".", 1)[0]
            doc = Document(
                user_id=user_id,
                title=title,
                filename=file.filename,
                text_content=text_content,
                page_count=page_count,
                source_type=source_type,
                pdf_data=file_bytes if source_type == "pdf" else None,
            )
            db.session.add(doc)
            db.session.flush()

            try:
                from rag import embed_document_chunks
                embed_document_chunks(doc)
            except Exception as embed_err:
                logging.warning(f"Chunk embedding failed for bulk-uploaded document {doc.id}: {embed_err}")

            results.append({
                "filename": file.filename,
                "success": True,
                "id": doc.id,
                "title": doc.title,
                "page_count": page_count,
            })
        except Exception as e:
            logging.error(f"Bulk upload failed for {file.filename}: {e}")
            results.append({
                "filename": file.filename,
                "success": False,
                "error": "Could not read this file",
            })

    db.session.commit()

    succeeded = [r for r in results if r["success"]]
    return jsonify(
        results=results,
        succeeded=len(succeeded),
        failed=len(results) - len(succeeded),
    )


@app.route("/documents/from-text", methods=["POST"])
@jwt_required()
def create_document_from_text():
    """Create a document from pasted/typed text (no file involved)."""
    data = request.get_json()
    raw_text = data.get("text", "")
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify(error="Please give this document a title so you can find it easily."), 400

    try:
        text_content, page_count = extract_text_from_plain_text(raw_text)
    except ValueError as e:
        return jsonify(error=str(e)), 400

    document = Document(
        user_id=int(get_jwt_identity()),
        title=title,
        filename=f"{title}.txt",
        text_content=text_content,
        page_count=page_count,
        source_type="text",
    )
    db.session.add(document)
    db.session.commit()

    # RAG: chunk + embed long documents so generation can retrieve the
    # most relevant portion instead of always truncating to the first
    # ~18k characters. Short documents skip this (see should_chunk).
    try:
        from rag import embed_document_chunks
        embed_document_chunks(document)
    except Exception as e:
        logging.warning(f"Chunk embedding failed for document {document.id}: {e}")

    return jsonify(
        id=document.id,
        title=document.title,
        page_count=document.page_count,
        source_type=document.source_type,
        uploaded_at=document.uploaded_at.isoformat(),
    )


@app.route("/documents/from-url", methods=["POST"])
@jwt_required()
@limiter.limit("20 per hour")
def create_document_from_url():
    """Create a document by fetching and extracting text from a web page."""
    data = request.get_json()
    url = (data.get("url") or "").strip()
    title = data.get("title")

    if not url:
        return jsonify(error="A URL is required"), 400
    if not (url.startswith("http://") or url.startswith("https://")):
        return jsonify(error="URL must start with http:// or https://"), 400

    try:
        text_content, page_count = extract_text_from_url(url)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        logging.error(f"URL extraction failed: {e}")
        return jsonify(error="Could not fetch or read this page"), 502

    if not title:
        return jsonify(error="Please give this document a title so you can find it easily."), 400

    document = Document(
        user_id=int(get_jwt_identity()),
        title=title,
        filename=url,
        text_content=text_content,
        page_count=page_count,
        source_type="url",
        source_url=url,
    )
    db.session.add(document)
    db.session.commit()

    # RAG: chunk + embed long documents so generation can retrieve the
    # most relevant portion instead of always truncating to the first
    # ~18k characters. Short documents skip this (see should_chunk).
    try:
        from rag import embed_document_chunks
        embed_document_chunks(document)
    except Exception as e:
        logging.warning(f"Chunk embedding failed for document {document.id}: {e}")

    return jsonify(
        id=document.id,
        title=document.title,
        page_count=document.page_count,
        source_type=document.source_type,
        source_url=document.source_url,
        uploaded_at=document.uploaded_at.isoformat(),
    )


@app.route("/documents/from-youtube", methods=["POST"])
@jwt_required()
@limiter.limit("10 per hour")
def create_document_from_youtube():
    """
    Create a document from a YouTube video. Tries captions first (fast,
    free); if none exist, falls back to downloading the audio and
    transcribing it via Gemini - meaningfully slower, so this is rate
    limited tighter than the plain URL endpoint.
    """
    data = request.get_json()
    url = (data.get("url") or "").strip()
    title = (data.get("title") or "").strip()

    if not url:
        return jsonify(error="A YouTube URL is required"), 400
    if not title:
        return jsonify(error="Please give this document a title so you can find it easily."), 400

    try:
        text_content, page_count = extract_text_from_youtube(
            url, transcribe_audio_fn=transcribe_audio
        )
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        logging.error(f"YouTube extraction failed: {e}")
        return jsonify(error="Could not process this YouTube video"), 502

    document = Document(
        user_id=int(get_jwt_identity()),
        title=title,
        filename=url,
        text_content=text_content,
        page_count=page_count,
        source_type="youtube",
        source_url=url,
    )
    db.session.add(document)
    db.session.commit()

    # RAG: chunk + embed long documents so generation can retrieve the
    # most relevant portion instead of always truncating to the first
    # ~18k characters. Short documents skip this (see should_chunk).
    try:
        from rag import embed_document_chunks
        embed_document_chunks(document)
    except Exception as e:
        logging.warning(f"Chunk embedding failed for document {document.id}: {e}")

    return jsonify(
        id=document.id,
        title=document.title,
        page_count=document.page_count,
        source_type=document.source_type,
        source_url=document.source_url,
        uploaded_at=document.uploaded_at.isoformat(),
    )


@app.route("/documents/from-audio", methods=["POST"])
@jwt_required()
@limiter.limit("10 per hour")
def create_document_from_audio():
    """Create a document by transcribing an uploaded audio file via Gemini."""
    if "file" not in request.files:
        return jsonify(error="No file uploaded (expected form field 'file')"), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify(error="No file selected"), 400

    title = (request.form.get("title") or "").strip()
    if not title:
        return jsonify(error="Please give this document a title so you can find it easily."), 400
    audio_bytes = file.read()

    try:
        text_content, page_count = extract_text_from_audio(
            audio_bytes, file.filename, transcribe_audio_fn=transcribe_audio
        )
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        logging.error(f"Audio transcription failed: {e}")
        return jsonify(error="Could not transcribe this audio file"), 502

    document = Document(
        user_id=int(get_jwt_identity()),
        title=title,
        filename=file.filename,
        text_content=text_content,
        page_count=page_count,
        source_type="audio",
    )
    db.session.add(document)
    db.session.commit()

    # RAG: chunk + embed long documents so generation can retrieve the
    # most relevant portion instead of always truncating to the first
    # ~18k characters. Short documents skip this (see should_chunk).
    try:
        from rag import embed_document_chunks
        embed_document_chunks(document)
    except Exception as e:
        logging.warning(f"Chunk embedding failed for document {document.id}: {e}")

    return jsonify(
        id=document.id,
        title=document.title,
        page_count=document.page_count,
        source_type=document.source_type,
        uploaded_at=document.uploaded_at.isoformat(),
    )


@app.route("/documents", methods=["GET"])
@jwt_required()
def list_documents():
    user_id = int(get_jwt_identity())
    documents = Document.query.filter_by(user_id=user_id).order_by(
        Document.uploaded_at.desc()
    ).all()
    return jsonify(
        documents=[
            {
                "id": d.id,
                "title": d.title,
                "filename": d.filename,
                "page_count": d.page_count,
                "source_type": d.source_type,
                "uploaded_at": d.uploaded_at.isoformat(),
            }
            for d in documents
        ]
    )


@app.route("/documents/<int:document_id>", methods=["GET"])
@jwt_required()
def get_document(document_id):
    user_id = int(get_jwt_identity())
    document = _get_owned_document(document_id, user_id)
    if not document:
        return jsonify(error="Document not found"), 404
    return jsonify(
        id=document.id,
        title=document.title,
        filename=document.filename,
        page_count=document.page_count,
        text_content=document.text_content,
        source_type=document.source_type,
        source_url=document.source_url,
        has_pdf=bool(document.pdf_data),
        uploaded_at=document.uploaded_at.isoformat(),
    )


@app.route("/documents/<int:document_id>/file", methods=["GET"])
@jwt_required()
def serve_document_file(document_id):
    """
    Serves the original uploaded PDF bytes so the Read tab can render it in
    a real PDF viewer instead of showing raw extracted text. Only available
    for PDF-sourced documents - other source types (text, URL, YouTube,
    audio) never had an original file to store.

    Reachable via ?token=... query param (in addition to the normal
    Authorization header) because <iframe src="..."> can't set custom
    headers - see JWT_TOKEN_LOCATION config above.
    """
    from flask import send_file
    import io
    user_id = int(get_jwt_identity())
    document = _get_owned_document(document_id, user_id)
    if not document:
        return jsonify(error="Document not found"), 404
    if not document.pdf_data:
        return jsonify(error="No original file available for this document"), 404

    return send_file(
        io.BytesIO(document.pdf_data),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=document.filename or "document.pdf",
    )


@app.route("/documents/<int:document_id>", methods=["DELETE"])
@jwt_required()
def delete_document(document_id):
    user_id = int(get_jwt_identity())
    document = _get_owned_document(document_id, user_id)
    if not document:
        return jsonify(error="Document not found"), 404

    # Cascades configured on the model relationships take care of deleting
    # every Quiz/Question/Attempt/Answer/StudySession tied to this document.
    db.session.delete(document)
    db.session.commit()
    return jsonify(message="Document deleted")


def _get_owned_document(document_id, user_id):
    return Document.query.filter_by(id=document_id, user_id=user_id).first()


# ---------------------------------------------------------------------------
# AI study aids (summary, key concepts, flashcards) - cached on Document
# ---------------------------------------------------------------------------
@app.route("/documents/<int:document_id>/summary", methods=["GET"])
@limiter.limit("20 per hour")
@jwt_required()
def document_summary(document_id):
    user_id = int(get_jwt_identity())
    document = _get_owned_document(document_id, user_id)
    if not document:
        return jsonify(error="Document not found"), 404

    if not document.summary:
        try:
            document.summary = generate_summary(
                get_prompt_text_for_document(document, "comprehensive study summary covering the whole document")
            )
            db.session.commit()
        except Exception as e:
            logging.error(f"Summary generation failed: {e}")
            return jsonify(error="Summary generation unavailable."), 502

    return jsonify(summary=document.summary)


@app.route("/documents/<int:document_id>/key-concepts", methods=["GET"])
@limiter.limit("20 per hour")
@jwt_required()
def document_key_concepts(document_id):
    user_id = int(get_jwt_identity())
    document = _get_owned_document(document_id, user_id)
    if not document:
        return jsonify(error="Document not found"), 404

    if not document.key_concepts:
        try:
            document.key_concepts = generate_key_concepts(
                get_prompt_text_for_document(document, "key concepts and important terms across the whole document")
            )
            db.session.commit()
        except Exception as e:
            logging.error(f"Key concepts generation failed: {e}")
            return jsonify(error="Key concepts generation unavailable."), 502

    return jsonify(key_concepts=document.key_concepts)


@app.route("/documents/<int:document_id>/flashcards", methods=["GET"])
@limiter.limit("20 per hour")
@jwt_required()
def document_flashcards(document_id):
    user_id = int(get_jwt_identity())
    document = _get_owned_document(document_id, user_id)
    if not document:
        return jsonify(error="Document not found"), 404

    if not document.flashcards:
        try:
            document.flashcards = generate_flashcards(
                get_prompt_text_for_document(document, "flashcards covering key facts across the whole document")
            )
            db.session.commit()
        except Exception as e:
            logging.error(f"Flashcard generation failed: {e}")
            return jsonify(error="Flashcard generation unavailable."), 502

    return jsonify(flashcards=document.flashcards)


@app.route("/documents/<int:document_id>/explainer", methods=["GET"])
@limiter.limit("10 per hour")
@jwt_required()
def document_explainer(document_id):
    """
    Returns a cached self-contained interactive HTML explainer page for this
    document, generated once by Gemini and cached on the Document row.
    The frontend renders it in a sandboxed iframe (allow-scripts only) so
    interactivity works but the page can't touch the app's own DOM or auth.
    """
    user_id = int(get_jwt_identity())
    document = _get_owned_document(document_id, user_id)
    if not document:
        return jsonify(error="Document not found"), 404

    if not document.explainer_html or request.args.get("force") == "1":
        try:
            document.explainer_html = generate_explainer(
                get_prompt_text_for_document(document, "interactive explainer covering the whole document")
            )
            db.session.commit()
        except ValueError as e:
            logging.error(f"Explainer generation produced invalid output: {e}")
            return jsonify(error="Explainer generation failed. Please try again."), 502
        except Exception as e:
            logging.error(f"Explainer generation failed: {e}")
            return jsonify(error="Explainer generation unavailable."), 502

    return jsonify(explainer_html=document.explainer_html)


# ---------------------------------------------------------------------------
# Study sessions (timer)
# ---------------------------------------------------------------------------
@app.route("/study-sessions", methods=["POST"])
@jwt_required()
def log_study_session():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    document_id = data.get("document_id")
    duration_seconds = data.get("duration_seconds")

    if not document_id or duration_seconds is None:
        return jsonify(error="document_id and duration_seconds are required"), 400

    if not _get_owned_document(document_id, user_id):
        return jsonify(error="Document not found"), 404

    try:
        duration_seconds = int(duration_seconds)
    except (TypeError, ValueError):
        return jsonify(error="duration_seconds must be a number"), 400

    if duration_seconds <= 0:
        return jsonify(error="duration_seconds must be positive"), 400

    session_record = StudySession(
        user_id=user_id, document_id=document_id, duration_seconds=duration_seconds
    )
    db.session.add(session_record)
    db.session.commit()

    total = (
        db.session.query(db.func.sum(StudySession.duration_seconds))
        .filter_by(user_id=user_id, document_id=document_id)
        .scalar()
        or 0
    )

    return jsonify(total_study_seconds=total)


# ---------------------------------------------------------------------------
# Quizzes
# ---------------------------------------------------------------------------
@app.route("/quizzes/config", methods=["GET"])
def quiz_config():
    """
    Returns the full structure for all four quiz modes so the frontend can
    render accurate descriptions without hardcoding mark/question counts.
    Every mode now has two format options (60 or 30 as the format_mode key).
    """
    def format_options(modes_dict, difficulty):
        return [
            get_quiz_plan(difficulty, fmt) for fmt in sorted(modes_dict.keys())
        ]

    return jsonify(
        easy=format_options(EASY_MODES, "easy"),
        hard=format_options(HARD_MODES, "hard"),
        difficult=format_options(DIFFICULT_MODES, "difficult"),
        pattern_trainer=format_options(PATTERN_TRAINER_MODES, "lecturer_style"),
    )


def _require_role(role):
    """Decorator factory: rejects the request unless the logged-in user has
    the given role. Must be applied inside (after) @jwt_required()."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = db.session.get(User, int(get_jwt_identity()))
            if not user or user.role != role:
                return jsonify(error=f"This action requires a {role} account"), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def _require_admin(fn):
    """Decorator: rejects the request unless the logged-in user has
    is_admin=True. Separate from _require_role since admin is a privilege
    layer on top of role (student/teacher), not a 3rd role value. Must be
    applied inside (after) @jwt_required()."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = db.session.get(User, int(get_jwt_identity()))
        if not user or not user.is_admin:
            return jsonify(error="Admin access required"), 403
        return fn(*args, **kwargs)
    return wrapper


@app.route("/quizzes/jobs/<job_id>", methods=["GET"])
@jwt_required()
def get_quiz_job_status(job_id):
    """
    Polled by the frontend after receiving a 202 from POST /quizzes for
    the Difficult tier. Returns pending/finished/failed. On finished,
    result contains {"quiz_id": ...} for the frontend to fetch the actual
    quiz via the normal GET /quizzes/:id.
    """
    from jobs import get_job_status
    status = get_job_status(job_id)
    if status is None:
        return jsonify(error="Background jobs are not available"), 503
    if status["status"] == "not_found":
        return jsonify(error="Job not found"), 404
    return jsonify(status)


@app.route("/quizzes", methods=["POST"])
@limiter.limit("15 per hour")
@jwt_required()
def create_quiz():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    document_id = data.get("document_id")
    difficulty = data.get("difficulty")
    format_mode = data.get("format_mode", data.get("easy_mode", 60))

    if difficulty not in ("easy", "hard", "difficult"):
        return jsonify(error="difficulty must be one of: easy, hard, difficult"), 400

    document = _get_owned_document(document_id, user_id)
    if not document:
        return jsonify(error="Document not found"), 404

    try:
        format_mode = int(format_mode)
    except (TypeError, ValueError):
        format_mode = 60

    text_for_prompt = get_prompt_text_for_document(document, f"{difficulty} difficulty quiz covering the whole document")

    # Difficult tier generates up to 70 questions in one Gemini call - slow
    # enough to risk a hung request or rate-limit timeout. Route it through
    # the background job queue when Redis is available; Easy/Hard are fast
    # enough that the added complexity of async isn't worth it for them.
    if difficulty == "difficult":
        from jobs import enqueue_quiz_generation
        job_id = enqueue_quiz_generation(
            document_id, difficulty, format_mode, user_id,
            is_assignment=False, title=None,
        )
        if job_id:
            return jsonify(job_id=job_id, status="pending"), 202

    try:
        plan, generated_questions = generate_quiz_questions(
            text_for_prompt, difficulty, format_mode
        )
    except ValueError as e:
        logging.error(f"Quiz generation failed: {e}")
        return jsonify(error="Failed to generate quiz. Please try again."), 502
    except Exception as e:
        logging.error(f"Quiz generation error: {e}")
        return jsonify(error="Quiz generation service unavailable."), 502

    quiz = Quiz(
        document_id=document.id,
        user_id=user_id,
        difficulty=difficulty,
        num_questions=len(generated_questions),
        total_marks=plan["total_marks"],
        time_limit_minutes=plan["time_limit_minutes"],
    )
    db.session.add(quiz)
    db.session.flush()  # get quiz.id

    for i, q in enumerate(generated_questions):
        question = Question(
            quiz_id=quiz.id,
            order_index=i,
            type=q.get("type", "mcq"),
            question_text=q.get("question", ""),
            options=q.get("options") if q.get("type") == "mcq" else None,
            correct_answer=str(q.get("correct_answer", "")),
            marks=int(q.get("marks", 1)),
            topic=q.get("topic"),
        )
        db.session.add(question)

    db.session.commit()

    return jsonify(_quiz_payload(quiz, include_answers=False))


@app.route("/quizzes/lecturer-style", methods=["POST"])
@limiter.limit("15 per hour")
@jwt_required()
def create_lecturer_style_quiz():
    """
    Question Pattern Trainer: generates pure MCQ questions from one document
    (course content), written to match the question-asking pattern found in
    a second document (the lecturer's past questions). Both documents must
    belong to the requesting user.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()
    content_document_id = data.get("content_document_id")
    style_document_id = data.get("style_document_id")
    format_mode = int(data.get("format_mode", data.get("easy_mode", 60)))
    if format_mode not in (60, 30):
        format_mode = 60

    if not content_document_id or not style_document_id:
        return jsonify(
            error="Both content_document_id and style_document_id are required"
        ), 400

    if content_document_id == style_document_id:
        return jsonify(
            error="Content and style documents must be different uploads"
        ), 400

    content_document = _get_owned_document(content_document_id, user_id)
    if not content_document:
        return jsonify(error="Content document not found"), 404

    style_document = _get_owned_document(style_document_id, user_id)
    if not style_document:
        return jsonify(error="Style (past questions) document not found"), 404

    content_text = get_prompt_text_for_document(content_document, "quiz content covering the whole document")
    style_text = get_prompt_text_for_document(style_document, "example past exam questions and phrasing style")

    try:
        plan, generated_questions = generate_lecturer_style_quiz_questions(
            content_text, style_text, format_mode
        )
    except ValueError as e:
        logging.error(f"Question pattern trainer generation failed: {e}")
        return jsonify(error="Failed to generate quiz. Please try again."), 502
    except Exception as e:
        logging.error(f"Question pattern trainer generation error: {e}")
        return jsonify(error="Quiz generation service unavailable."), 502

    quiz = Quiz(
        document_id=content_document.id,
        user_id=user_id,
        difficulty="lecturer_style",
        num_questions=len(generated_questions),
        total_marks=plan["total_marks"],
        time_limit_minutes=plan["time_limit_minutes"],
    )
    db.session.add(quiz)
    db.session.flush()

    for i, q in enumerate(generated_questions):
        question = Question(
            quiz_id=quiz.id,
            order_index=i,
            type=q.get("type", "mcq"),
            question_text=q.get("question", ""),
            options=q.get("options") if q.get("type") == "mcq" else None,
            correct_answer=str(q.get("correct_answer", "")),
            marks=int(q.get("marks", 1)),
            topic=q.get("topic"),
        )
        db.session.add(question)

    db.session.commit()

    return jsonify(_quiz_payload(quiz, include_answers=False))


def _quiz_payload(quiz, include_answers=False, shuffle_seed=None):
    """
    shuffle_seed: when provided, question ORDER is shuffled deterministically
    from that seed - stable across repeated fetches of the SAME attempt (a
    page refresh mid-quiz won't reorder things underneath the student), but
    different between different students/attempts. This matters most for
    assignments: many students take the exact same underlying Quiz row, and
    without this every one of them sees identical question order, making it
    trivial to call out answers by position ("question 3 is B") to people
    sitting nearby.

    MCQ option order is deliberately NOT shuffled here: each Question's
    correct_answer is stored as a fixed key (e.g. "B") and grading (see
    grading.py) compares the submitted key directly against that stored
    value. Shuffling option positions without also threading the same
    shuffle through grading would silently mis-grade every shuffled
    question - a correctness bug, not just a cosmetic one. Reordering
    which QUESTION comes first carries no such risk since each Question
    keeps its own correct_answer regardless of list position.
    """
    import random

    questions_list = list(quiz.questions)
    if shuffle_seed is not None:
        random.Random(shuffle_seed).shuffle(questions_list)

    questions = []
    for q in questions_list:
        item = {
            "id": q.id,
            "order_index": q.order_index,
            "type": q.type,
            "question": q.question_text,
            "marks": q.marks,
        }
        if q.type == "mcq":
            item["options"] = q.options
        if include_answers:
            item["correct_answer"] = q.correct_answer
        questions.append(item)

    return {
        "id": quiz.id,
        "document_id": quiz.document_id,
        "difficulty": quiz.difficulty,
        "num_questions": quiz.num_questions,
        "total_marks": quiz.total_marks,
        "time_limit_minutes": quiz.time_limit_minutes,
        "created_at": quiz.created_at.isoformat(),
        "is_assignment": quiz.is_assignment,
        "is_published": quiz.is_published,
        "join_code": quiz.join_code,
        "title": quiz.title,
        "questions": questions,
    }


def _generate_join_code():
    """6-character uppercase alphanumeric code, regenerated on the rare
    collision (checked by the caller)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I to avoid confusion
    return "".join(secrets.choice(alphabet) for _ in range(6))


# ---------------------------------------------------------------------------
# Classes / Cohorts (teacher-created groups)
# ---------------------------------------------------------------------------

@app.route("/classes", methods=["POST"])
@jwt_required()
@_require_role("teacher")
def create_class():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(error="Class name is required"), 400

    join_code = _generate_join_code()
    for _ in range(5):
        if not Class.query.filter_by(join_code=join_code).first():
            break
        join_code = _generate_join_code()

    class_ = Class(
        teacher_id=user_id,
        name=name,
        description=(data.get("description") or "").strip() or None,
        join_code=join_code,
    )
    db.session.add(class_)
    db.session.commit()
    return jsonify(_class_payload(class_))


@app.route("/classes", methods=["GET"])
@jwt_required()
def list_classes():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if user.role == "teacher":
        classes = Class.query.filter_by(teacher_id=user_id).all()
    else:
        memberships = ClassMembership.query.filter_by(student_id=user_id).all()
        classes = [m.class_ for m in memberships]

    return jsonify(classes=[_class_payload(c) for c in classes])


@app.route("/classes/<int:class_id>", methods=["GET"])
@jwt_required()
def get_class(class_id):
    user_id = int(get_jwt_identity())
    class_ = _get_accessible_class(class_id, user_id)
    if not class_:
        return jsonify(error="Class not found"), 404
    return jsonify(_class_payload(class_, include_members=True, include_assignments=True))


@app.route("/classes/<int:class_id>", methods=["DELETE"])
@jwt_required()
@_require_role("teacher")
def delete_class(class_id):
    user_id = int(get_jwt_identity())
    class_ = Class.query.filter_by(id=class_id, teacher_id=user_id).first()
    if not class_:
        return jsonify(error="Class not found"), 404
    db.session.delete(class_)
    db.session.commit()
    return jsonify(message="Class deleted")


@app.route("/classes/join", methods=["POST"])
@jwt_required()
def join_class():
    user_id = int(get_jwt_identity())
    join_code = (request.get_json().get("join_code") or "").strip().upper()
    class_ = Class.query.filter_by(join_code=join_code).first()
    if not class_:
        return jsonify(error="Invalid class code"), 404

    existing = ClassMembership.query.filter_by(
        class_id=class_.id, student_id=user_id
    ).first()
    if existing:
        return jsonify(message="Already a member", class_=_class_payload(class_))

    membership = ClassMembership(class_id=class_.id, student_id=user_id)
    db.session.add(membership)
    db.session.commit()
    return jsonify(message="Joined class", class_=_class_payload(class_, include_assignments=True))


@app.route("/classes/<int:class_id>/assignments", methods=["POST"])
@jwt_required()
@_require_role("teacher")
def add_class_assignment(class_id):
    """Tag a published assignment to a class so all members can see it."""
    user_id = int(get_jwt_identity())
    class_ = Class.query.filter_by(id=class_id, teacher_id=user_id).first()
    if not class_:
        return jsonify(error="Class not found"), 404

    quiz_id = request.get_json().get("quiz_id")
    quiz = Quiz.query.filter_by(id=quiz_id, user_id=user_id, is_assignment=True, is_published=True).first()
    if not quiz:
        return jsonify(error="Assignment not found or not published"), 404

    existing = ClassAssignment.query.filter_by(class_id=class_id, quiz_id=quiz_id).first()
    if existing:
        return jsonify(message="Already tagged to this class")

    ca = ClassAssignment(class_id=class_id, quiz_id=quiz_id)
    db.session.add(ca)
    db.session.commit()
    return jsonify(message="Assignment added to class")


@app.route("/classes/<int:class_id>/assignments/<int:quiz_id>", methods=["DELETE"])
@jwt_required()
@_require_role("teacher")
def remove_class_assignment(class_id, quiz_id):
    user_id = int(get_jwt_identity())
    class_ = Class.query.filter_by(id=class_id, teacher_id=user_id).first()
    if not class_:
        return jsonify(error="Class not found"), 404
    ca = ClassAssignment.query.filter_by(class_id=class_id, quiz_id=quiz_id).first()
    if not ca:
        return jsonify(error="Assignment not tagged to this class"), 404
    db.session.delete(ca)
    db.session.commit()
    return jsonify(message="Assignment removed from class")


def _get_accessible_class(class_id, user_id):
    class_ = Class.query.get(class_id)
    if not class_:
        return None
    if class_.teacher_id == user_id:
        return class_
    if ClassMembership.query.filter_by(class_id=class_id, student_id=user_id).first():
        return class_
    return None


def _class_payload(class_, include_members=False, include_assignments=False):
    payload = {
        "id": class_.id,
        "name": class_.name,
        "description": class_.description,
        "join_code": class_.join_code,
        "created_at": class_.created_at.isoformat(),
        "member_count": len(class_.memberships),
    }
    if include_members:
        payload["members"] = [
            {"student_id": m.student_id, "joined_at": m.joined_at.isoformat()}
            for m in class_.memberships
        ]
    if include_assignments:
        cas = ClassAssignment.query.filter_by(class_id=class_.id).all()
        payload["assignments"] = [
            _quiz_payload(ca_row.quiz if hasattr(ca_row, "quiz") else
                         Quiz.query.get(ca_row.quiz_id), include_answers=False)
            for ca_row in cas
            if Quiz.query.get(ca_row.quiz_id)
        ]
    return payload


@app.route("/assignments", methods=["POST"])
@limiter.limit("15 per hour")
@jwt_required()
@_require_role("teacher")
def create_assignment():
    """
    Teacher-only: generate a quiz draft from one of the teacher's own
    documents. NOT published yet - the teacher reviews/edits/deletes
    questions via /assignments/:id/questions, then calls
    /assignments/:id/publish to make the join code live for students.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()
    document_id = data.get("document_id")
    difficulty = data.get("difficulty")
    format_mode = data.get("format_mode", data.get("easy_mode", 60))
    title = (data.get("title") or "").strip()

    if difficulty not in ("easy", "hard", "difficult"):
        return jsonify(error="difficulty must be one of: easy, hard, difficult"), 400

    document = _get_owned_document(document_id, user_id)
    if not document:
        return jsonify(error="Document not found"), 404

    try:
        format_mode = int(format_mode)
    except (TypeError, ValueError):
        format_mode = 60

    text_for_prompt = get_prompt_text_for_document(document, f"{difficulty} difficulty quiz covering the whole document")

    try:
        plan, generated_questions = generate_quiz_questions(
            text_for_prompt, difficulty, format_mode
        )
    except ValueError as e:
        logging.error(f"Assignment quiz generation failed: {e}")
        return jsonify(error="Failed to generate quiz. Please try again."), 502
    except Exception as e:
        logging.error(f"Assignment quiz generation error: {e}")
        return jsonify(error="Quiz generation service unavailable."), 502

    # Generate a unique join code now, but it won't work for students
    # (_get_accessible_quiz / join checks is_published) until the teacher
    # explicitly publishes - generating it upfront means the teacher can
    # see/share it from the review screen without an extra step later.
    join_code = _generate_join_code()
    for _ in range(5):
        if not Quiz.query.filter_by(join_code=join_code).first():
            break
        join_code = _generate_join_code()

    quiz = Quiz(
        document_id=document.id,
        user_id=user_id,
        difficulty=difficulty,
        num_questions=len(generated_questions),
        total_marks=plan["total_marks"],
        time_limit_minutes=plan["time_limit_minutes"],
        is_assignment=True,
        is_published=False,
        join_code=join_code,
        title=title or document.title,
    )
    db.session.add(quiz)
    db.session.flush()

    for i, q in enumerate(generated_questions):
        question = Question(
            quiz_id=quiz.id,
            order_index=i,
            type=q.get("type", "mcq"),
            question_text=q.get("question", ""),
            options=q.get("options") if q.get("type") == "mcq" else None,
            correct_answer=str(q.get("correct_answer", "")),
            marks=int(q.get("marks", 1)),
            topic=q.get("topic"),
        )
        db.session.add(question)

    db.session.commit()

    # Include answers in the draft response - the teacher reviewing it
    # needs to see correct answers/model answers, unlike a student.
    return jsonify(_quiz_payload(quiz, include_answers=True))


@app.route("/assignments/<int:quiz_id>/questions", methods=["GET"])
@jwt_required()
@_require_role("teacher")
def get_assignment_questions(quiz_id):
    """Teacher-only: fetch all questions (with answers) for review/editing."""
    user_id = int(get_jwt_identity())
    quiz = Quiz.query.filter_by(
        id=quiz_id, user_id=user_id, is_assignment=True
    ).first()
    if not quiz:
        return jsonify(error="Assignment not found"), 404

    return jsonify(_quiz_payload(quiz, include_answers=True))


@app.route("/assignments/<int:quiz_id>/questions/<int:question_id>", methods=["PATCH"])
@jwt_required()
@_require_role("teacher")
def edit_assignment_question(quiz_id, question_id):
    """
    Teacher-only: edit a single question's text/options/correct answer/marks
    before publishing. Only allowed while the assignment is still a draft -
    editing a published quiz's questions after students may have already
    answered them would corrupt grading.
    """
    user_id = int(get_jwt_identity())
    quiz = Quiz.query.filter_by(
        id=quiz_id, user_id=user_id, is_assignment=True
    ).first()
    if not quiz:
        return jsonify(error="Assignment not found"), 404
    if quiz.is_published:
        return jsonify(
            error="Can't edit questions on a published assignment"
        ), 400

    question = Question.query.filter_by(id=question_id, quiz_id=quiz.id).first()
    if not question:
        return jsonify(error="Question not found"), 404

    data = request.get_json()
    if "question_text" in data:
        question.question_text = data["question_text"]
    if "options" in data and question.type == "mcq":
        question.options = data["options"]
    if "correct_answer" in data:
        question.correct_answer = str(data["correct_answer"])
    if "marks" in data:
        try:
            question.marks = int(data["marks"])
        except (TypeError, ValueError):
            return jsonify(error="marks must be an integer"), 400

    db.session.commit()

    # Recalculate total marks in case this question's marks changed
    quiz.total_marks = sum(q.marks for q in quiz.questions)
    db.session.commit()

    return jsonify(_quiz_payload(quiz, include_answers=True))


@app.route("/assignments/<int:quiz_id>/questions/<int:question_id>", methods=["DELETE"])
@jwt_required()
@_require_role("teacher")
def delete_assignment_question(quiz_id, question_id):
    """Teacher-only: remove a question from a draft assignment entirely."""
    user_id = int(get_jwt_identity())
    quiz = Quiz.query.filter_by(
        id=quiz_id, user_id=user_id, is_assignment=True
    ).first()
    if not quiz:
        return jsonify(error="Assignment not found"), 404
    if quiz.is_published:
        return jsonify(
            error="Can't delete questions from a published assignment"
        ), 400

    question = Question.query.filter_by(id=question_id, quiz_id=quiz.id).first()
    if not question:
        return jsonify(error="Question not found"), 404

    db.session.delete(question)
    db.session.commit()

    quiz.num_questions = len(quiz.questions)
    quiz.total_marks = sum(q.marks for q in quiz.questions)
    db.session.commit()

    return jsonify(_quiz_payload(quiz, include_answers=True))


@app.route("/assignments/<int:quiz_id>/publish", methods=["POST"])
@jwt_required()
@_require_role("teacher")
def publish_assignment(quiz_id):
    """
    Teacher-only: makes the join code live for students. Requires at least
    one question to remain (a teacher could delete every question while
    reviewing, which shouldn't be publishable).
    """
    user_id = int(get_jwt_identity())
    quiz = Quiz.query.filter_by(
        id=quiz_id, user_id=user_id, is_assignment=True
    ).first()
    if not quiz:
        return jsonify(error="Assignment not found"), 404
    if quiz.is_published:
        return jsonify(error="Assignment is already published"), 409
    if not quiz.questions:
        return jsonify(
            error="Can't publish an assignment with no questions left"
        ), 400

    quiz.is_published = True
    db.session.commit()

    return jsonify(_quiz_payload(quiz, include_answers=True))


@app.route("/assignments", methods=["GET"])
@jwt_required()
@_require_role("teacher")
def list_assignments():
    """Teacher-only: every assignment quiz this teacher has created, with
    a student attempt count for each so the dashboard can show activity
    at a glance without a separate request per assignment."""
    user_id = int(get_jwt_identity())
    quizzes = (
        Quiz.query.filter_by(user_id=user_id, is_assignment=True)
        .order_by(Quiz.created_at.desc())
        .all()
    )

    result = []
    for quiz in quizzes:
        attempt_count = Attempt.query.filter_by(
            quiz_id=quiz.id
        ).filter(Attempt.submitted_at.isnot(None)).count()
        result.append(
            {
                "id": quiz.id,
                "title": quiz.title,
                "difficulty": quiz.difficulty,
                "join_code": quiz.join_code,
                "num_questions": quiz.num_questions,
                "total_marks": quiz.total_marks,
                "created_at": quiz.created_at.isoformat(),
                "submitted_attempt_count": attempt_count,
                "is_published": quiz.is_published,
            }
        )

    return jsonify(assignments=result)


@app.route("/assignments/<int:quiz_id>/results", methods=["GET"])
@jwt_required()
@_require_role("teacher")
def assignment_results(quiz_id):
    """Teacher-only: every student's submitted attempt on one of this
    teacher's assignments, most recent first."""
    user_id = int(get_jwt_identity())
    quiz = Quiz.query.filter_by(
        id=quiz_id, user_id=user_id, is_assignment=True
    ).first()
    if not quiz:
        return jsonify(error="Assignment not found"), 404

    attempts = (
        Attempt.query.filter_by(quiz_id=quiz.id)
        .filter(Attempt.submitted_at.isnot(None))
        .order_by(Attempt.submitted_at.desc())
        .all()
    )

    results = []
    for a in attempts:
        student = db.session.get(User, a.user_id)
        results.append(
            {
                "attempt_id": a.id,
                "student_username": student.username if student else "Unknown",
                "total_score": a.total_score,
                "max_score": a.max_score,
                "percentage": a.percentage,
                "submitted_at": a.submitted_at.isoformat(),
            }
        )

    return jsonify(
        assignment={
            "id": quiz.id,
            "title": quiz.title,
            "difficulty": quiz.difficulty,
            "join_code": quiz.join_code,
            "total_marks": quiz.total_marks,
        },
        results=results,
    )


@app.route("/assignments/join", methods=["POST"])
@jwt_required()
def join_assignment():
    """
    Student-facing: redeem a join code to get the quiz to attempt. Does
    NOT require the student to own the source document - that's the whole
    point of an assignment quiz. Works for either role, since nothing
    stops a teacher from also trying a colleague's assignment, and there's
    no harm in allowing it.
    """
    data = request.get_json()
    join_code = (data.get("join_code") or "").strip().upper()

    if not join_code:
        return jsonify(error="A join code is required"), 400

    quiz = Quiz.query.filter_by(join_code=join_code, is_assignment=True).first()
    if not quiz or not quiz.is_published:
        return jsonify(error="Invalid or expired join code"), 404

    return jsonify(_quiz_payload(quiz, include_answers=False))


def _get_accessible_quiz(quiz_id, user_id):
    """
    A quiz is accessible to a user if either:
      - they created it (personal self-study quiz, OR the teacher's own
        assignment draft/published quiz - the owner can always see it), or
      - it's a PUBLISHED teacher-assigned quiz (is_assignment=True AND
        is_published=True) - any student with the join code/link can fetch
        and attempt it, not just the teacher who created it. A draft
        assignment (is_published=False) is only visible to its owner.
    """
    quiz = Quiz.query.filter_by(id=quiz_id).first()
    if not quiz:
        return None
    if quiz.user_id == user_id:
        return quiz
    if quiz.is_assignment and quiz.is_published:
        return quiz
    return None


@app.route("/quizzes/<int:quiz_id>", methods=["GET"])
@jwt_required()
def get_quiz(quiz_id):
    user_id = int(get_jwt_identity())
    quiz = _get_accessible_quiz(quiz_id, user_id)
    if not quiz:
        return jsonify(error="Quiz not found"), 404

    # Shuffle question order per (quiz, student) - stable for this student
    # across the whole attempt (refreshing mid-quiz won't reorder things),
    # but different from every other student taking the same assignment.
    # The quiz's own creator sees the canonical, unshuffled order when
    # reviewing/previewing their own quiz.
    shuffle_seed = None
    if quiz.user_id != user_id:
        shuffle_seed = hash((quiz_id, user_id))

    return jsonify(_quiz_payload(quiz, include_answers=False, shuffle_seed=shuffle_seed))


# ---------------------------------------------------------------------------
# Attempts
# ---------------------------------------------------------------------------
@app.route("/attempts", methods=["POST"])
@jwt_required()
def start_attempt():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    quiz_id = data.get("quiz_id")

    quiz = _get_accessible_quiz(quiz_id, user_id)
    if not quiz:
        return jsonify(error="Quiz not found"), 404

    total_study_seconds = (
        db.session.query(db.func.sum(StudySession.duration_seconds))
        .filter_by(user_id=user_id, document_id=quiz.document_id)
        .scalar()
        or 0
    )

    attempt = Attempt(
        quiz_id=quiz.id,
        user_id=user_id,
        max_score=quiz.total_marks,
        study_time_seconds=total_study_seconds,
    )
    db.session.add(attempt)
    db.session.commit()

    return jsonify(
        attempt_id=attempt.id,
        time_limit_minutes=quiz.time_limit_minutes,
        started_at=attempt.started_at.isoformat(),
    )


@app.route("/attempts/<int:attempt_id>/submit-mcq", methods=["POST"])
@jwt_required()
def submit_mcq_phase(attempt_id):
    """
    Phase 1 of the gated flow (Stage 3 — Difficult only): grade the MCQ
    section and lock those answers in. The theory section then becomes
    available. For MCQ-only quizzes this endpoint shouldn't be called —
    use /submit directly.
    """
    user_id = int(get_jwt_identity())
    attempt = Attempt.query.filter_by(id=attempt_id, user_id=user_id).first()
    if not attempt:
        return jsonify(error="Attempt not found"), 404
    if attempt.submitted_at is not None:
        return jsonify(error="This attempt is already fully submitted"), 409
    if attempt.mcq_submitted_at is not None:
        return jsonify(error="MCQ section already submitted"), 409

    quiz = attempt.quiz
    if quiz.difficulty not in ("difficult",):
        return jsonify(
            error="This quiz doesn't use the gated MCQ→theory flow"
        ), 400

    data = request.get_json()
    submitted_answers = {
        a["question_id"]: a.get("answer")
        for a in data.get("answers", [])
        if "question_id" in a
    }

    mcq_questions = [q for q in quiz.questions if q.type == "mcq"]
    mcq_score = 0

    for q in mcq_questions:
        user_answer = submitted_answers.get(q.id)
        score, is_correct = grade_mcq(q, user_answer)
        mcq_score += score
        answer = Answer(
            attempt_id=attempt.id,
            question_id=q.id,
            user_answer=user_answer,
            score_awarded=score,
            is_correct=is_correct,
        )
        db.session.add(answer)

    attempt.mcq_submitted_at = datetime.utcnow()
    attempt.mcq_score = mcq_score
    db.session.commit()

    mcq_max = sum(q.marks for q in mcq_questions)
    theory_questions = [q for q in quiz.questions if q.type == "theory"]

    return jsonify(
        attempt_id=attempt.id,
        mcq_score=mcq_score,
        mcq_max=mcq_max,
        mcq_percentage=round((mcq_score / mcq_max) * 100, 1) if mcq_max else 0,
        theory_questions=[
            {
                "id": q.id,
                "question": q.question_text,
                "marks": q.marks,
                "type": "theory",
            }
            for q in theory_questions
        ],
    )


@app.route("/attempts/<int:attempt_id>/submit", methods=["POST"])
@jwt_required()
def submit_attempt(attempt_id):
    """
    For MCQ-only quizzes (Easy, Hard, Pattern Trainer): grades and finalizes
    the entire attempt in one step — same as before.

    For Stage 3 — Difficult (MCQ + theory): this is called after
    submit-mcq, submitting only the theory answers. MCQ answers were already
    locked in; this adds the theory scores and computes the final result.
    """
    user_id = int(get_jwt_identity())
    attempt = Attempt.query.filter_by(id=attempt_id, user_id=user_id).first()
    if not attempt:
        return jsonify(error="Attempt not found"), 404
    if attempt.submitted_at is not None:
        return jsonify(error="This attempt was already submitted"), 409

    quiz = attempt.quiz
    has_theory = any(q.type == "theory" for q in quiz.questions)

    # For gated flow: MCQ must have been submitted first
    if has_theory and attempt.mcq_submitted_at is None:
        return jsonify(
            error="Submit the MCQ section first via /submit-mcq"
        ), 400

    data = request.get_json()
    submitted_answers = {
        a["question_id"]: a.get("answer")
        for a in data.get("answers", [])
        if "question_id" in a
    }

    if has_theory:
        # Gated flow: only grade the theory questions here (MCQ already done)
        theory_questions = [q for q in quiz.questions if q.type == "theory"]
        theory_batch = [
            (q, submitted_answers.get(q.id)) for q in theory_questions
        ]

        if theory_batch:
            items = [
                {
                    "question_text": q.question_text,
                    "model_answer": q.correct_answer,
                    "marks": q.marks,
                    "user_answer": ua,
                }
                for q, ua in theory_batch
            ]
            try:
                results = grade_theory_batch(items)
            except Exception as e:
                logging.error(f"Theory grading failed: {e}")
                results = [
                    {"score": 0, "feedback": "Automatic grading unavailable."}
                    for _ in theory_batch
                ]

            for (q, ua), result in zip(theory_batch, results):
                answer = Answer(
                    attempt_id=attempt.id,
                    question_id=q.id,
                    user_answer=ua,
                    score_awarded=result["score"],
                    feedback=result.get("feedback"),
                )
                db.session.add(answer)

        # Total = MCQ score already saved + new theory score
        theory_score = sum(
            r["score"] for r in results
        ) if theory_batch else 0
        total_score = (attempt.mcq_score or 0) + theory_score

    else:
        # MCQ-only: grade everything in one go (unchanged from before)
        questions = quiz.questions
        answer_records = {}

        for q in questions:
            user_answer = submitted_answers.get(q.id)
            score, is_correct = grade_mcq(q, user_answer)
            answer = Answer(
                attempt_id=attempt.id,
                question_id=q.id,
                user_answer=user_answer,
                score_awarded=score,
                is_correct=is_correct,
            )
            db.session.add(answer)
            answer_records[q.id] = answer

        total_score = sum(a.score_awarded for a in answer_records.values())

    percentage = round((total_score / attempt.max_score) * 100, 1) if attempt.max_score else 0
    attempt.total_score = total_score
    attempt.percentage = percentage
    attempt.submitted_at = datetime.utcnow()
    db.session.commit()

    new_achievements = check_and_unlock_achievements(user_id)
    breakdown = _build_breakdown(attempt)

    if new_achievements:
        user = db.session.get(User, user_id)
        for ach in new_achievements:
            try:
                import threading
                threading.Thread(
                    target=send_achievement_email,
                    args=(
                        user.email, user.username,
                        ach.get("name", ach.get("key", "New Achievement")),
                        ach.get("description", "You've hit a new milestone!"),
                    ),
                    daemon=True,
                ).start()
            except Exception as e:
                logging.warning(f"Achievement email failed for {user.username}: {e}")

    return jsonify(
        attempt_id=attempt.id,
        total_score=total_score,
        max_score=attempt.max_score,
        percentage=percentage,
        study_time_seconds=attempt.study_time_seconds,
        breakdown=breakdown,
        new_achievements=new_achievements,
    )


def _build_breakdown(attempt):
    """Builds the per-question breakdown list for an attempt, using the
    persisted Answer rows. Works for both a just-submitted attempt and one
    being re-fetched later for history/review."""
    answers_by_question = {a.question_id: a for a in attempt.answers}

    breakdown = []
    for q in attempt.quiz.questions:
        a = answers_by_question.get(q.id)
        item = {
            "question_id": q.id,
            "question": q.question_text,
            "type": q.type,
            "marks": q.marks,
            "topic": q.topic,
            "score_awarded": a.score_awarded if a else 0,
            "user_answer": a.user_answer if a else None,
        }
        if q.type == "mcq":
            item["correct_answer"] = q.correct_answer
            item["options"] = q.options
            item["is_correct"] = a.is_correct if a else None
        else:
            item["model_answer"] = q.correct_answer
            item["feedback"] = a.feedback if a else None
        item["explanation"] = a.explanation if a else None
        breakdown.append(item)

    return breakdown


@app.route("/attempts/<int:attempt_id>", methods=["GET"])
@jwt_required()
def get_attempt(attempt_id):
    """Full detail for a past attempt - used by History/Results to review
    or retake a quiz without needing React Router navigation state."""
    user_id = int(get_jwt_identity())
    attempt = Attempt.query.filter_by(id=attempt_id, user_id=user_id).first()
    if not attempt:
        return jsonify(error="Attempt not found"), 404
    if attempt.submitted_at is None:
        return jsonify(error="This attempt has not been submitted yet"), 409

    return jsonify(
        attempt_id=attempt.id,
        quiz_id=attempt.quiz_id,
        document_id=attempt.quiz.document_id,
        document_title=attempt.quiz.document.title,
        difficulty=attempt.quiz.difficulty,
        total_score=attempt.total_score,
        max_score=attempt.max_score,
        percentage=attempt.percentage,
        study_time_seconds=attempt.study_time_seconds,
        submitted_at=attempt.submitted_at.isoformat(),
        breakdown=_build_breakdown(attempt),
    )


@app.route("/attempts/<int:attempt_id>/explain", methods=["POST"])
@limiter.limit("20 per hour")
@jwt_required()
def explain_attempt(attempt_id):
    """Generates (or returns cached) plain-language explanations for every
    question the user got less than full marks on."""
    user_id = int(get_jwt_identity())
    attempt = Attempt.query.filter_by(id=attempt_id, user_id=user_id).first()
    if not attempt:
        return jsonify(error="Attempt not found"), 404
    if attempt.submitted_at is None:
        return jsonify(error="This attempt has not been submitted yet"), 409

    answers_by_question = {a.question_id: a for a in attempt.answers}

    # Only explain questions that lost marks, and only generate for ones
    # that don't already have a cached explanation.
    to_explain = []  # (question, answer)
    for q in attempt.quiz.questions:
        a = answers_by_question.get(q.id)
        if a and a.score_awarded < q.marks and not a.explanation:
            to_explain.append((q, a))

    if to_explain:
        items = []
        for q, a in to_explain:
            item = {
                "type": q.type,
                "question_text": q.question_text,
                "marks": q.marks,
                "score_awarded": a.score_awarded,
                "user_answer": a.user_answer,
            }
            if q.type == "mcq":
                item["options"] = q.options
                item["correct_answer"] = q.correct_answer
            else:
                item["model_answer"] = q.correct_answer
                item["feedback"] = a.feedback
            items.append(item)

        try:
            explanations = explain_mistakes_batch(items)
        except Exception as e:
            logging.error(f"Explain mistakes failed: {e}")
            return jsonify(error="Explanation service unavailable."), 502

        for (q, a), explanation in zip(to_explain, explanations):
            a.explanation = explanation

        db.session.commit()

    return jsonify(breakdown=_build_breakdown(attempt))


@app.route("/attempts/<int:attempt_id>/export-pdf", methods=["GET"])
@jwt_required()
def export_results_pdf(attempt_id):
    """Download a printable PDF results card for this attempt."""
    from flask import send_file
    from pdf_export import generate_results_pdf
    user_id = int(get_jwt_identity())
    attempt = Attempt.query.filter_by(id=attempt_id, user_id=user_id).first()
    if not attempt or not attempt.submitted_at:
        return jsonify(error="Attempt not found"), 404

    user = db.session.get(User, user_id)
    breakdown = _build_breakdown(attempt)
    try:
        pdf_bytes = generate_results_pdf(attempt, attempt.quiz, breakdown, user.username)
    except Exception as e:
        logging.error(f"PDF results export failed: {e}")
        return jsonify(error="PDF generation failed"), 502

    buf = __import__("io").BytesIO(pdf_bytes)
    safe_title = (attempt.quiz.title or "results").replace(" ", "_")[:40]
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                     download_name=f"{safe_title}_results.pdf")


@app.route("/documents/<int:document_id>/export-study-guide", methods=["GET"])
@jwt_required()
def export_study_guide_pdf(document_id):
    """Download a printable PDF study guide (summary + key concepts + flashcards)."""
    from flask import send_file
    from pdf_export import generate_study_guide_pdf
    user_id = int(get_jwt_identity())
    document = _get_owned_document(document_id, user_id)
    if not document:
        return jsonify(error="Document not found"), 404
    if not document.summary and not document.key_concepts and not document.flashcards:
        return jsonify(error="Generate the study aids first (Summary, Key Concepts, or Flashcards tabs)"), 400

    try:
        pdf_bytes = generate_study_guide_pdf(
            document, document.summary, document.key_concepts, document.flashcards
        )
    except Exception as e:
        logging.error(f"PDF study guide export failed: {e}")
        return jsonify(error="PDF generation failed"), 502

    buf = __import__("io").BytesIO(pdf_bytes)
    safe_title = document.title.replace(" ", "_")[:40]
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                     download_name=f"{safe_title}_study_guide.pdf")


@app.route("/attempts", methods=["GET"])
@jwt_required()
def list_attempts():
    user_id = int(get_jwt_identity())
    attempts = (
        Attempt.query.filter_by(user_id=user_id)
        .filter(Attempt.submitted_at.isnot(None))
        .order_by(Attempt.submitted_at.desc())
        .all()
    )

    return jsonify(
        attempts=[
            {
                "id": a.id,
                "quiz_id": a.quiz_id,
                "document_id": a.quiz.document_id,
                "document_title": a.quiz.document.title,
                "difficulty": a.quiz.difficulty,
                "total_score": a.total_score,
                "max_score": a.max_score,
                "percentage": a.percentage,
                "study_time_seconds": a.study_time_seconds,
                "submitted_at": a.submitted_at.isoformat(),
            }
            for a in attempts
        ]
    )


# ---------------------------------------------------------------------------
# Performance analytics
# ---------------------------------------------------------------------------
DIFFICULTY_ORDER = ["easy", "hard", "difficult"]

# Tuned to be a clear signal, not a hair-trigger: needs a real run of
# strong (or weak) results before suggesting a change, and looks only at
# the most recent attempts on THIS difficulty so a one-off bad day on
# Hard doesn't get averaged away by a long history of doing well on Easy.
RECOMMENDATION_LOOKBACK = 3
STEP_UP_THRESHOLD = 80
STEP_DOWN_THRESHOLD = 45


def _recommend_difficulty(document_id, user_id):
    """
    Looks at the student's most recent attempts on this document, AT
    THEIR CURRENT/LAST-USED DIFFICULTY, and suggests stepping up or down
    one tier if performance is consistently strong or weak. Returns None
    if there isn't enough history yet, or if performance doesn't clearly
    warrant a change - this is meant to fire rarely and meaningfully, not
    on every quiz.
    """
    recent_attempts = (
        Attempt.query.join(Quiz)
        .filter(
            Quiz.document_id == document_id,
            Attempt.user_id == user_id,
            Attempt.submitted_at.isnot(None),
        )
        .order_by(Attempt.submitted_at.desc())
        .limit(RECOMMENDATION_LOOKBACK)
        .all()
    )

    if len(recent_attempts) < RECOMMENDATION_LOOKBACK:
        return None  # not enough history on this document yet

    last_difficulty = recent_attempts[0].quiz.difficulty

    # Lecturer Style isn't a tier on the easy/hard/difficult ladder - there's
    # no "step up/down" concept for it, so no recommendation applies when
    # that's the most recent difficulty used on this document.
    if last_difficulty not in DIFFICULTY_ORDER:
        return None

    # Only consider attempts at the same difficulty as the most recent one,
    # so a step-up suggestion isn't triggered by mixing in old Easy scores
    # after the student has already moved to Hard, and vice versa.
    same_tier_attempts = [
        a for a in recent_attempts if a.quiz.difficulty == last_difficulty
    ]
    if len(same_tier_attempts) < RECOMMENDATION_LOOKBACK:
        return None

    avg_percentage = sum(a.percentage for a in same_tier_attempts) / len(
        same_tier_attempts
    )

    current_index = DIFFICULTY_ORDER.index(last_difficulty)

    if avg_percentage >= STEP_UP_THRESHOLD and current_index < len(DIFFICULTY_ORDER) - 1:
        suggested = DIFFICULTY_ORDER[current_index + 1]
        return {
            "suggested_difficulty": suggested,
            "current_difficulty": last_difficulty,
            "direction": "up",
            "average_percentage": round(avg_percentage, 1),
            "based_on_attempts": len(same_tier_attempts),
        }

    if avg_percentage <= STEP_DOWN_THRESHOLD and current_index > 0:
        suggested = DIFFICULTY_ORDER[current_index - 1]
        return {
            "suggested_difficulty": suggested,
            "current_difficulty": last_difficulty,
            "direction": "down",
            "average_percentage": round(avg_percentage, 1),
            "based_on_attempts": len(same_tier_attempts),
        }

    return None  # performance is fine where it is - no suggestion needed


@app.route("/documents/<int:document_id>/recommended-difficulty", methods=["GET"])
@jwt_required()
def recommended_difficulty(document_id):
    user_id = int(get_jwt_identity())
    document = _get_owned_document(document_id, user_id)
    if not document:
        return jsonify(error="Document not found"), 404

    recommendation = _recommend_difficulty(document_id, user_id)
    return jsonify(recommendation=recommendation)


@app.route("/documents/<int:document_id>/mastery", methods=["GET"])
@jwt_required()
def document_mastery(document_id):
    """
    Per-topic mastery breakdown for this student on this document: for
    every topic tag seen across all of the student's submitted attempts,
    aggregate marks earned vs marks possible. Questions without a topic
    (older quizzes generated before this field existed, or any generation
    where the AI omitted it) are grouped under "General" rather than
    silently dropped, so totals always add up.
    """
    user_id = int(get_jwt_identity())
    document = _get_owned_document(document_id, user_id)
    if not document:
        return jsonify(error="Document not found"), 404

    attempts = (
        Attempt.query.join(Quiz)
        .filter(
            Quiz.document_id == document_id,
            Attempt.user_id == user_id,
            Attempt.submitted_at.isnot(None),
        )
        .all()
    )

    topic_stats = {}  # topic -> {"earned": float, "possible": int, "attempts": int}

    for attempt in attempts:
        answers_by_question = {a.question_id: a for a in attempt.answers}
        for q in attempt.quiz.questions:
            answer = answers_by_question.get(q.id)
            if not answer:
                continue
            topic = q.topic or "General"
            if topic not in topic_stats:
                topic_stats[topic] = {"earned": 0, "possible": 0, "questions_seen": 0}
            topic_stats[topic]["earned"] += answer.score_awarded or 0
            topic_stats[topic]["possible"] += q.marks
            topic_stats[topic]["questions_seen"] += 1

    topics = []
    for topic, stats in topic_stats.items():
        mastery_pct = (
            round((stats["earned"] / stats["possible"]) * 100, 1)
            if stats["possible"] > 0
            else 0
        )
        topics.append(
            {
                "topic": topic,
                "mastery_percentage": mastery_pct,
                "questions_seen": stats["questions_seen"],
            }
        )

    # Weakest first - that's the order a student actually wants to see
    # when deciding what to focus on.
    topics.sort(key=lambda t: t["mastery_percentage"])

    return jsonify(topics=topics)


@app.route("/documents/<int:document_id>/weak-spots-quiz", methods=["POST"])
@limiter.limit("15 per hour")
@jwt_required()
def create_weak_spots_quiz(document_id):
    """
    Generates a short, focused practice quiz on the student's weakest
    topics for this document, derived from their own mastery data.
    Requires at least 2 distinct topics below 70% mastery with at least
    2 questions seen each - otherwise there isn't enough signal yet to
    target anything meaningfully, and a generic quiz is more useful.
    """
    user_id = int(get_jwt_identity())
    document = _get_owned_document(document_id, user_id)
    if not document:
        return jsonify(error="Document not found"), 404

    # Reuse the same topic aggregation logic as /mastery directly rather
    # than making an HTTP self-call.
    attempts = (
        Attempt.query.join(Quiz)
        .filter(
            Quiz.document_id == document_id,
            Attempt.user_id == user_id,
            Attempt.submitted_at.isnot(None),
        )
        .all()
    )
    topic_stats = {}
    for attempt in attempts:
        answers_by_question = {a.question_id: a for a in attempt.answers}
        for q in attempt.quiz.questions:
            answer = answers_by_question.get(q.id)
            if not answer:
                continue
            topic = q.topic or "General"
            if topic not in topic_stats:
                topic_stats[topic] = {"earned": 0, "possible": 0, "questions_seen": 0}
            topic_stats[topic]["earned"] += answer.score_awarded or 0
            topic_stats[topic]["possible"] += q.marks
            topic_stats[topic]["questions_seen"] += 1

    weak_topics = [
        topic
        for topic, stats in topic_stats.items()
        if stats["possible"] > 0
        and (stats["earned"] / stats["possible"]) * 100 < 70
        and stats["questions_seen"] >= 2
        and topic != "General"
    ]

    if len(weak_topics) < 1:
        return jsonify(
            error="Not enough quiz history yet to identify weak topics. "
            "Take a few more quizzes on this document first."
        ), 400

    # Cap at 5 topics so the prompt stays focused rather than diluted
    weak_topics = weak_topics[:5]

    weak_topics_str = ", ".join(weak_topics)
    text_for_prompt = get_prompt_text_for_document(document, f"quiz focused on these weak topics: {weak_topics_str}")

    try:
        plan, generated_questions = generate_weak_spots_quiz(
            text_for_prompt, weak_topics
        )
    except ValueError as e:
        logging.error(f"Weak-spots quiz generation failed: {e}")
        return jsonify(error=str(e)), 502
    except Exception as e:
        logging.error(f"Weak-spots quiz generation error: {e}")
        return jsonify(error="Quiz generation service unavailable."), 502

    quiz = Quiz(
        document_id=document.id,
        user_id=user_id,
        difficulty="weak_spots",
        num_questions=len(generated_questions),
        total_marks=plan["total_marks"],
        time_limit_minutes=plan["time_limit_minutes"],
        title=f"Weak spots: {', '.join(weak_topics[:3])}"
        + ("..." if len(weak_topics) > 3 else ""),
    )
    db.session.add(quiz)
    db.session.flush()

    for i, q in enumerate(generated_questions):
        question = Question(
            quiz_id=quiz.id,
            order_index=i,
            type=q.get("type", "mcq"),
            question_text=q.get("question", ""),
            options=q.get("options") if q.get("type") == "mcq" else None,
            correct_answer=str(q.get("correct_answer", "")),
            marks=int(q.get("marks", 1)),
            topic=q.get("topic"),
        )
        db.session.add(question)

    db.session.commit()

    return jsonify(_quiz_payload(quiz, include_answers=False))


@app.route("/documents/<int:document_id>/performance", methods=["GET"])
@jwt_required()
def document_performance(document_id):
    user_id = int(get_jwt_identity())
    document = _get_owned_document(document_id, user_id)
    if not document:
        return jsonify(error="Document not found"), 404

    attempts = (
        Attempt.query.join(Quiz)
        .filter(
            Quiz.document_id == document_id,
            Attempt.user_id == user_id,
            Attempt.submitted_at.isnot(None),
        )
        .order_by(Attempt.submitted_at.asc())
        .all()
    )

    total_study_seconds = (
        db.session.query(db.func.sum(StudySession.duration_seconds))
        .filter_by(user_id=user_id, document_id=document_id)
        .scalar()
        or 0
    )

    return jsonify(
        document_id=document_id,
        document_title=document.title,
        total_study_seconds=total_study_seconds,
        attempts=[
            {
                "attempt_id": a.id,
                "difficulty": a.quiz.difficulty,
                "percentage": a.percentage,
                "study_time_seconds": a.study_time_seconds,
                "submitted_at": a.submitted_at.isoformat(),
            }
            for a in attempts
        ],
    )


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------
# Every route below requires is_admin=True (see _require_admin) - a
# privilege layer separate from role (student/teacher), not self-service.
# An admin account is created by setting is_admin=True directly in the
# database for now; see README for the one-time SQL.

@app.route("/admin/overview", methods=["GET"])
@jwt_required()
@_require_admin
def admin_overview():
    return jsonify(get_admin_overview())


@app.route("/admin/users", methods=["GET"])
@jwt_required()
@_require_admin
def admin_users():
    search = request.args.get("search")
    return jsonify(users=get_admin_users(search=search))


@app.route("/admin/users/<int:user_id>", methods=["GET"])
@jwt_required()
@_require_admin
def admin_user_detail(user_id):
    detail = get_admin_user_detail(user_id)
    if not detail:
        return jsonify(error="User not found"), 404
    return jsonify(detail)


@app.route("/admin/content", methods=["GET"])
@jwt_required()
@_require_admin
def admin_content():
    search = request.args.get("search")
    return jsonify(documents=get_admin_content(search=search))


@app.route("/admin/content/<int:document_id>", methods=["DELETE"])
@jwt_required()
@_require_admin
def admin_delete_content(document_id):
    """Admin moderation: delete any document platform-wide, regardless of
    owner. Cascades the same way the owner's own delete does."""
    document = db.session.get(Document, document_id)
    if not document:
        return jsonify(error="Document not found"), 404
    db.session.delete(document)
    db.session.commit()
    return jsonify(message="Document deleted")


@app.route("/admin/usage", methods=["GET"])
@jwt_required()
@_require_admin
def admin_usage():
    return jsonify(get_admin_usage())


@app.cli.command("create-admin")
@click.argument("username")
def create_admin(username):
    """Grant admin privileges to an existing user. Usage: flask create-admin <username>"""
    user = User.query.filter_by(username=username).first()
    if not user:
        click.echo(f"No user found with username '{username}'")
        return
    if user.is_admin:
        click.echo(f"{username} is already an admin")
        return
    user.is_admin = True
    db.session.commit()
    click.echo(f"{username} is now an admin")


if __name__ == "__main__":
    app.run(debug=True)