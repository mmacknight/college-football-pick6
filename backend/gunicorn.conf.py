# Gunicorn configuration for Pick6 dev server
import multiprocessing

# Server socket
bind = "0.0.0.0:3001"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1  # Usually 3-5 workers on most machines
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100

# Restart workers after this many requests (prevent memory leaks)
preload_app = True

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Process naming
proc_name = "pick6-api"

# Development settings
reload = True  # Auto-reload on code changes
reload_extra_files = [
    "lambdas/",
    "scripts/",
]

print(f"🚀 Gunicorn will start {workers} workers for better performance")
