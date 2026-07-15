"""
Background job queue for slow AI generation calls (RQ + Redis).

Problem this solves: quiz generation for the larger tiers (Difficult =
70 questions in one Gemini call) can take real time, and under Gemini
rate limits a synchronous request can hang or 502 with no retry. Moving
generation into a worker process means the HTTP request returns
immediately with a job ID, and the frontend polls for completion instead
of holding a connection open.

Setup: requires a Redis instance (REDIS_URL env var). On Render, add a
Redis add-on (free tier available) and set REDIS_URL to its connection
string. Locally, `redis-server` running on the default port works with
no config needed.

Running the worker: a SEPARATE process from the Flask web process.
    python3 worker.py
On Render this means a second service (a "worker" type, not "web") running
the same codebase with that start command.

Graceful degradation: if REDIS_URL isn't set or Redis is unreachable,
get_queue() returns None and callers fall back to synchronous generation
(the original behavior) rather than the app refusing to generate quizzes
at all. This matters for local dev where spinning up Redis is friction
most people won't bother with unless they're specifically testing this.
"""
import os
import logging
import json

_redis_conn = None
_queue = None


def get_redis_connection():
    global _redis_conn
    if _redis_conn is not None:
        return _redis_conn

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return None

    try:
        import redis
        _redis_conn = redis.from_url(redis_url)
        _redis_conn.ping()  # fail fast if unreachable, don't discover it mid-request
        return _redis_conn
    except Exception as e:
        logging.warning(f"Redis unavailable, falling back to synchronous generation: {e}")
        return None


def get_queue():
    global _queue
    if _queue is not None:
        return _queue

    conn = get_redis_connection()
    if conn is None:
        return None

    from rq import Queue
    _queue = Queue("studymate-generation", connection=conn)
    return _queue


def enqueue_quiz_generation(document_id, difficulty, format_mode, user_id, is_assignment=False, title=None):
    """
    Enqueues quiz generation as a background job. Returns the job_id.
    The actual work happens in jobs_worker.generate_quiz_job, running in
    a separate `python3 worker.py` process.
    """
    queue = get_queue()
    if queue is None:
        return None

    job = queue.enqueue(
        "jobs_worker.generate_quiz_job",
        document_id, difficulty, format_mode, user_id, is_assignment, title,
        job_timeout="5m",  # Difficult-tier 70-question generation can genuinely take a while
    )
    return job.id

def enqueue_email(fn_name, *args):
    """
    Enqueues any of the send_*_email functions from email_utils as a
    background job, instead of a raw daemon thread. Daemon threads get
    killed instantly (no exception, no log) if the gunicorn worker
    recycles or the process restarts mid-send - which happens often on
    a frequently-redeployed app - silently dropping emails with zero
    trace. RQ jobs live in Redis and survive the web process entirely,
    so a mid-flight deploy doesn't lose the email.

    Falls back to sending synchronously (blocking the request briefly,
    ~1-3 seconds) if Redis isn't available - still correct, just not async.
    """
    queue = get_queue()
    if queue is None:
        # No Redis - fall back to sending synchronously right here rather
        # than silently dropping the email or using an unreliable thread.
        import email_utils
        try:
            getattr(email_utils, fn_name)(*args)
        except Exception as e:
            logging.warning(f"Synchronous email fallback failed for {fn_name}: {e}")
        return None

    job = queue.enqueue(
        "jobs_worker.send_email_job",
        fn_name, args,
        job_timeout="30s",
    )
    return job.id


def get_job_status(job_id):
    """
    Returns {"status": "pending"|"finished"|"failed", "result": ...} for
    a previously enqueued job. Frontend polls this endpoint until status
    is finished or failed.
    """
    queue = get_queue()
    if queue is None:
        return None

    from rq.job import Job
    conn = get_redis_connection()
    try:
        job = Job.fetch(job_id, connection=conn)
    except Exception:
        return {"status": "not_found"}

    if job.is_finished:
        return {"status": "finished", "result": job.result}
    if job.is_failed:
        return {"status": "failed", "error": str(job.exc_info)[-500:] if job.exc_info else "Generation failed"}
    return {"status": "pending"}
