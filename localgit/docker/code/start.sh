#!/bin/bash
set -e

echo "Starting Local Git Server with Flask API..."

# Ensure socket dir exists with correct permissions
mkdir -p /var/run
chown www-data:www-data /var/run

# Start fcgiwrap for git-http-backend (handles Git smart HTTP protocol)
spawn-fcgi -s /var/run/fcgiwrap.socket -M 766 /usr/sbin/fcgiwrap || true

# Start Flask dev server for API (background) - fine for local lightweight use
python app.py &

# Give Flask a moment to start
sleep 2

echo "Flask API ready on http://localhost/api/"
echo "Git repos served at http://localhost/git/<name>.git"
echo ""

# Start nginx in foreground
exec nginx -g "daemon off;"
