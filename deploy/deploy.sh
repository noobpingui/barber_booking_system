#!/bin/bash
# deploy.sh — pull latest code and restart the app on the EC2 instance.
#
# Usage (run from the project root on the server):
#   bash deploy/deploy.sh

set -e  # exit immediately on any error

APP_DIR="/home/ubuntu/barber_booking_system"
VENV="$APP_DIR/venv/bin"

echo "==> Pulling latest code..."
cd "$APP_DIR"
git pull origin main

echo "==> Installing/updating dependencies..."
"$VENV/pip" install -e .

echo "==> Running database migrations..."
"$VENV/alembic" upgrade head

echo "==> Restarting app..."
sudo systemctl restart barber

echo "==> Done. Check status with: sudo journalctl -u barber -f"
