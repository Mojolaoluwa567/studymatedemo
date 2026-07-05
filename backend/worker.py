"""
RQ worker entry point - run as a SEPARATE process from the Flask web app:
    python3 worker.py

On Render, this becomes a second service (type: "Worker", not "Web
Service") in the same repo, with this as its start command. It needs the
same environment variables as the web service (GEMINI_API_KEY, DATABASE_URL,
REDIS_URL, etc.) since it independently connects to the database and Gemini.
"""
import os
import logging
from redis import Redis
from rq import Worker, Queue

logging.basicConfig(level=logging.INFO)

redis_url = os.environ.get("REDIS_URL")
if not redis_url:
    raise RuntimeError(
        "REDIS_URL is required to run the worker. Set it to your Redis "
        "connection string (e.g. redis://localhost:6379 locally, or the "
        "Redis add-on's connection string on Render)."
    )

conn = Redis.from_url(redis_url)

if __name__ == "__main__":
    queue = Queue("studymate-generation", connection=conn)
    worker = Worker([queue], connection=conn)
    logging.info("StudyMate background worker started, listening for jobs...")
    worker.work()
