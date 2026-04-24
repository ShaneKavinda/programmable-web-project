# Gunicorn Configuration File
# Production-ready WSGI server configuration for Flask application

import os

# Server socket configuration
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes configuration
# Keep defaults memory-friendly for container environments.
# Override via env vars without rebuilding image
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")
threads = int(os.getenv("GUNICORN_THREADS", "2"))
worker_connections = int(os.getenv("GUNICORN_WORKER_CONNECTIONS", "200"))
timeout = 30
keepalive = 2
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "100"))

# Process naming and user
proc_name = "gunicorn_flask_app"

# Logging configuration
accesslog = "-"  # STDOUT for Docker logging
errorlog = "-"   # STDOUT for Docker logging
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL configuration (can be enabled when deployed with SSL)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Server hooks (can be customized if needed)
# def on_starting(server):
#     """Called just before the master process is initialized."""
#     pass

# def on_exit(server):
#     """Called just before exiting Gunicorn."""
#     pass

# Application configuration
wsgi_app = "ticket_management_system.app:app"

