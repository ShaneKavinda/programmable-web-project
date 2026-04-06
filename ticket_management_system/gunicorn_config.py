# Gunicorn Configuration File
# Production-ready WSGI server configuration for Flask application

import multiprocessing
import os

# Server socket configuration
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes configuration
# Default to a small worker count for micro instances unless overridden.
default_workers = min(3, (multiprocessing.cpu_count() * 2) + 1)
workers = int(os.getenv("WEB_CONCURRENCY", default_workers))
worker_class = "sync"  # Synchronous workers suitable for I/O-bound Flask apps
worker_connections = 1000
timeout = int(os.getenv("GUNICORN_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "2"))

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

