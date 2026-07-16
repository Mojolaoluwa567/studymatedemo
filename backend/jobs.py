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


def has_active_worker():
    """
    Checks if at least one RQ worker process is currently alive and
    listening. If not, enqueueing a job would leave it stuck in Redis
    forever with nothing to process it - better to run it synchronously
    right here than silently drop it. Self-healing: the moment a real
    worker process is added later, this starts returning True and jobs
    switch to running async automatically, with no code changes needed.
    """
    conn = get_redis_connection()
    if conn is None:
        return False
    try:
        from rq import Worker
        return len(Worker.all(connection=conn)) > 0
    except Exception as e:
        logging.warning(f"Could not check for active RQ workers: {e}")
        return False


def enqueue_quiz_generation(document_id, difficulty, format_mode, user_id, is_assignment=False, title=None):
    """
    Enqueues quiz generation as a background job. Returns the job_id, or
    None if there's no queue OR no active worker to process it - the
    caller (create_quiz route) already falls back to synchronous
    generation when this returns None, so this degrades gracefully either
    way rather than silently hanging.
    """
    queue = get_queue()
    if queue is None or not has_active_worker():
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
    background job when a real RQ worker is available. If not, falls
    back to a background THREAD rather than running inline - email
    sending must never block the actual signup/login/etc. response,
    since a slow or hanging SMTP connection would otherwise tie up one
    of a small number of web workers, potentially making the whole app
    unresponsive. send_email now has its own timeout (10s) so even in
    the worst case this can't hang indefinitely.
    """
    queue = get_queue()
    if queue is None or not has_active_worker():
        import threading
        import email_utils

        def _run():
            try:
                getattr(email_utils, fn_name)(*args)
            except Exception as e:
                logging.warning(f"Background email thread failed for {fn_name}: {e}")

        threading.Thread(target=_run, daemon=True).start()
        return None
    


    job = queue.enqueue(f"email_utils.{fn_name}", *args)
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