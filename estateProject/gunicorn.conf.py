# Gunicorn configuration for production
# =====================================
# Run: gunicorn -c gunicorn.conf.py estateProject.wsgi:application

import multiprocessing
import os

# ==============================================================================
# SERVER SOCKET
# ==============================================================================
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')
backlog = 2048

# ==============================================================================
# WORKER PROCESSES
# ==============================================================================
# Formula: (2 x CPU cores) + 1 for sync workers
# For async workers (gevent/eventlet): 4-12 x CPU cores
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))

# Worker class options:
# - sync: Default, one request at a time per worker
# - gevent: Async, handles many concurrent connections (recommended for I/O bound)
# - eventlet: Similar to gevent
# - uvicorn.workers.UvicornWorker: For ASGI (async Django)
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'sync')

# For gevent/eventlet, increase worker connections
worker_connections = 1000

# Thread pool (for gthread worker)
threads = int(os.environ.get('GUNICORN_THREADS', 4))

# ==============================================================================
# WORKER LIFECYCLE
# ==============================================================================
# Maximum requests before worker restart (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 100  # Random jitter to prevent all workers restarting at once

# Worker timeout (seconds)
timeout = 30  # Kill worker if no response in 30s
graceful_timeout = 30  # Time to finish current requests on shutdown
keepalive = 5  # Keep connection alive for X seconds

# ==============================================================================
# SERVER MECHANICS
# ==============================================================================
# Preload application (shared memory, faster worker startup)
# Warning: Be careful with database connections
preload_app = True

# Daemonize (run in background)
daemon = False

# User/Group to run as (security)
# user = 'www-data'
# group = 'www-data'

# ==============================================================================
# LOGGING
# ==============================================================================
# Log to stdout for container environments
accesslog = '-'  # stdout
errorlog = '-'   # stderr
loglevel = 'info'

# Access log format
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# ==============================================================================
# PROCESS NAMING
# ==============================================================================
proc_name = 'estate-app'

# ==============================================================================
# SSL (if terminating SSL at Gunicorn)
# ==============================================================================
# keyfile = '/path/to/key.pem'
# certfile = '/path/to/cert.pem'
# ssl_version = 'TLSv1_2'
# ciphers = 'TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256'

# ==============================================================================
# SERVER HOOKS
# ==============================================================================

def on_starting(server):
    """Called just before the master process is initialized."""
    pass

def on_reload(server):
    """Called before reloading the app."""
    pass

def when_ready(server):
    """Called just after the server is started."""
    pass

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    # Close any inherited database connections
    try:
        from django.db import connections
        for conn in connections.all():
            conn.close()
    except:
        pass

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    pass

def worker_int(worker):
    """Called when worker receives INT or QUIT signal."""
    pass

def worker_abort(worker):
    """Called when worker receives SIGABRT signal (timeout)."""
    pass

def pre_exec(server):
    """Called just before a new master process is forked."""
    pass

def child_exit(server, worker):
    """Called when a worker has been exited."""
    pass

def worker_exit(server, worker):
    """Called when a worker has been exited."""
    # Close database connections
    try:
        from django.db import connections
        for conn in connections.all():
            conn.close()
    except:
        pass
