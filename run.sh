#!/bin/sh

# ========================================
#   DBMS Project - Flask + Cloudflared
#   Compatible with bash, zsh, sh, dash
# ========================================

echo "========================================"
echo "   DBMS Project - Flask + Cloudflared"
echo "========================================"
echo

# Change to script directory (POSIX safe)
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR" || exit 1

# ---------- Check Python ----------
if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] Python3 is not installed or not in PATH"
  exit 1
fi

# ---------- Create venv if missing ----------
if [ ! -d ".venv" ]; then
  echo "[1/4] Creating virtual environment..."
  python3 -m venv .venv || {
    echo "[ERROR] Failed to create virtual environment"
    exit 1
  }
fi

# ---------- Activate venv ----------
echo "[2/4] Activating virtual environment..."
. .venv/bin/activate || {
  echo "[ERROR] Failed to activate virtual environment"
  exit 1
}

# ---------- Install requirements ----------
echo "[3/4] Installing requirements..."
pip install --upgrade pip >/dev/null 2>&1
pip install -r requirements.txt >/dev/null 2>&1 ||
  echo "[WARNING] Some packages may not have installed correctly"

# ---------- Export env vars ----------
export PORT=5000
export USE_WAITRESS=1

# ---------- Start Flask app ----------
echo "[4/4] Starting Flask app..."
python3 app.py &
FLASK_PID=$!

echo
echo "Waiting 2 seconds for Flask to start..."
sleep 2

# ---------- Open browser ----------
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:5000/"
elif command -v open >/dev/null 2>&1; then
  open "http://localhost:5000/"
else
  echo "Open http://localhost:5000 manually."
fi

# ---------- Cloudflared logic ----------
echo
echo "========================================"
echo "   Checking Cloudflared Installation..."
echo "========================================"
echo

if command -v cloudflared >/dev/null 2>&1; then
  echo "Cloudflared found. Starting secure tunnel..."
  echo "Your public URL will appear below:"
  echo
  cloudflared tunnel --url http://localhost:5000
  echo
  echo "Cloudflared tunnel stopped."
else
  echo "[WARNING] Cloudflared not installed."
  echo "Running ONLY on local network:"
  echo "    http://localhost:5000"
  echo
  echo "To enable public URLs, install Cloudflared:"
  echo "https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
fi

echo
echo "Flask app is still running (PID: $FLASK_PID)."
echo "Press Ctrl+C to stop."

wait "$FLASK_PID"
