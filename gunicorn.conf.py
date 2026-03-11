# Gunicorn configuration for production deployment on EC2 t3.nano.
# Run with: gunicorn app.main:app -c gunicorn.conf.py

# ── Binding ────────────────────────────────────────────────────────────────────
# Bind to localhost only — Nginx handles the public-facing port.
bind = "127.0.0.1:8000"

# ── Workers ────────────────────────────────────────────────────────────────────
# t3.nano has 1 vCPU and 512 MB RAM.
# 2 workers balances concurrency with memory constraints.
# Formula guideline: (2 x num_cpus) + 1 = 3, but 2 is safer at this RAM size.
workers = 2
worker_class = "uvicorn.workers.UvicornWorker"

# ── Timeouts ───────────────────────────────────────────────────────────────────
timeout = 30        # kill worker if it takes longer than 30s to respond
keepalive = 5       # keep idle connections alive for 5s (helps Nginx keep-alive)

# ── Logging ────────────────────────────────────────────────────────────────────
# "-" sends logs to stdout/stderr so systemd's journald captures them.
accesslog = "-"
errorlog = "-"
loglevel = "info"

# ── Proxy ──────────────────────────────────────────────────────────────────────
# Trust X-Forwarded-For headers from Nginx (safe since we bind to 127.0.0.1).
forwarded_allow_ips = "127.0.0.1"
