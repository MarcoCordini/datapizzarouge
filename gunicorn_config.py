"""
Gunicorn configuration for DataPizzaRouge API - Production
"""
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000  # Restart workers after this many requests (prevents memory leaks)
max_requests_jitter = 50  # Random jitter to prevent all workers restarting at once
timeout = 120  # Workers silent for more than this are killed and restarted
keepalive = 5  # Wait this long for requests on Keep-Alive connections

# Logging
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "datapizzarouge"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (se necessario)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Graceful timeout for workers
graceful_timeout = 30

# Preload app for better performance
preload_app = True
