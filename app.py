"""
TestProbe AI - Main Flask Application
"""

import os
import sys
import time
import logging
import psutil
from datetime import datetime
from urllib.parse import urlparse

from flask import Flask, request, jsonify, render_template

try:
    from flask_cors import CORS
    HAS_CORS = True
except ImportError:
    HAS_CORS = False

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    HAS_LIMITER = True
except ImportError:
    HAS_LIMITER = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from chatbot import process_message

# ── Logging Setup ─────────────────────────────────────────────
# ✅ Fix Unicode/Emoji encoding on Windows
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            "logs/testprobe.log",
            encoding="utf-8"   # ✅ Fix emoji encoding
        ),
        logging.StreamHandler(
            stream=open(
                os.devnull, "w"
            ) if sys.platform == "win32"
            else sys.stdout
        )
    ]
)

# ✅ Windows safe console logger (no emojis)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")
)

# Safe emit for Windows
original_emit = console_handler.emit
def safe_emit(record):
    try:
        record.msg = record.msg.encode(
            "ascii", "replace"
        ).decode("ascii")
        original_emit(record)
    except Exception:
        pass

console_handler.emit = safe_emit

root_logger = logging.getLogger()
root_logger.handlers = []
root_logger.addHandler(
    logging.FileHandler("logs/testprobe.log", encoding="utf-8")
)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)

# ── Flask App ─────────────────────────────────────────────────
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "testprobe-secret-key"),
    MAX_CONTENT_LENGTH=1 * 1024 * 1024,
    JSON_SORT_KEYS=False
)

if HAS_CORS:
    CORS(app)

if HAS_LIMITER:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )

app_start_time = datetime.now()

# ── Helpers ───────────────────────────────────────────────────
def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url.strip())
        return all([
            result.scheme in ("http", "https"),
            result.netloc,
            len(url) <= 500
        ])
    except Exception:
        return False

# ── Middleware ────────────────────────────────────────────────
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - getattr(
        request, "start_time", time.time()
    )
    logger.info(
        f"{response.status_code} | "
        f"{request.method} {request.path} | "
        f"{duration:.3f}s"
    )
    response.headers.update({
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options":        "DENY",
        "Cache-Control":          "no-store"
    })
    return response

# ── Routes ────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health", methods=["GET"])
def health_check():
    uptime = (datetime.now() - app_start_time).seconds
    return jsonify({
        "status":         "healthy",
        "version":        "2.0.0",
        "uptime_seconds": uptime,
        "timestamp":      datetime.now().isoformat()
    }), 200

@app.route("/test", methods=["POST"])
def test_game():
    data = request.get_json(silent=True)

    if not data or "message" not in data:
        return jsonify({
            "type":  "error",
            "reply": "No message provided."
        }), 400

    user_message = str(data["message"]).strip()

    if not user_message:
        return jsonify({
            "type":  "error",
            "reply": "Message cannot be empty."
        }), 400

    if not is_valid_url(user_message):
        return jsonify({
            "type":  "error",
            "reply": "Invalid URL. Please enter a valid HTTP or HTTPS URL."
        }), 400

    try:
        logger.info(f"Starting test for: {user_message}")
        response_data = process_message(user_message)
        return jsonify(response_data), 200

    except TimeoutError:
        return jsonify({
            "type":  "error",
            "reply": "Test timed out. Please try again."
        }), 504

    except ConnectionError:
        return jsonify({
            "type":  "error",
            "reply": "Connection failed. Please check the URL."
        }), 502

    except Exception as e:
        logger.error(f"Error: {str(e)[:100]}")
        return jsonify({
            "type":  "error",
            "reply": f"An error occurred: {str(e)[:100]}"
        }), 500

@app.route("/history", methods=["GET"])
def get_history():
    try:
        from chatbot import get_test_history
        history = get_test_history()
        return jsonify({
            "total":   len(history),
            "history": history
        }), 200
    except Exception:
        return jsonify({
            "total": 0, "history": []
        }), 200

# ── Error Handlers ────────────────────────────────────────────
@app.errorhandler(400)
def bad_request(e):
    return jsonify({
        "type": "error", "reply": "Bad request."
    }), 400

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "type": "error", "reply": "Not found."
    }), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "type": "error", "reply": "Server error."
    }), 500

# ── Entry Point ───────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Starting TestProbe AI on port {port}")
    print(f"Open: http://localhost:{port}")
    app.run(
        debug=True,
        port=port,
        host="0.0.0.0",
        threaded=True    # ✅ Handle requests in threads
    )