"""
Gunicorn production config for Render.

workers: default Gunicorn worker count is 1, meaning the whole app
handles ONE request at a time. If one student's PDF upload takes a few
seconds to process, every other request (including other students trying
to log in or upload) queues behind it and times out client-side - this
is the "load failed with multiple users" symptom.
"""
workers = 3
worker_class = "sync"
timeout = 120
keepalive = 5
max_requests = 500
max_requests_jitter = 50