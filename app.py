"""
TestProbe AI - Main Flask Application
"""

import os
import sys
import time
import logging
from datetime import datetime
from urllib.parse import urlparse

from flask import Flask, request, jsonify, render_template, session

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
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/testprobe.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# ── Flask App ─────────────────────────────────────────────────
app = Flask(__name__, template_folder='templates')
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "testprobe-secret-key-2024"),
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


def get_session_id() -> str:
    """Get or create unique session ID for conversation tracking"""
    if "session_id" not in session:
        import uuid
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


# ── Middleware ────────────────────────────────────────────────
@app.before_request
def before_request():
    request.start_time = time.time()


@app.after_request
def after_request(response):
    duration = time.time() - getattr(request, "start_time", time.time())
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
        "version":        "3.0.0",
        "uptime_seconds": uptime,
        "timestamp":      datetime.now().isoformat()
    }), 200


@app.route("/test", methods=["POST"])
def test_game():
    """
    Unified endpoint for both:
    - Game URL testing
    - Follow-up chat questions about tested game
    """
    data = request.get_json(silent=True)
    logger.info(f"Received request data: {data}")

    if not data or "message" not in data:
        logger.error("No message in request")
        return jsonify({
            "type":  "error",
            "reply": "No message provided."
        }), 400

    user_message = str(data["message"]).strip()
    logger.info(f"Processing message: {user_message[:80]}")

    if not user_message:
        return jsonify({
            "type":  "error",
            "reply": "Message cannot be empty."
        }), 400

    # ── Get session ID for conversation tracking ──
    session_id = get_session_id()

    try:
        # process_message handles BOTH URLs and chat questions
        # No URL validation block here anymore!
        response_data = process_message(user_message, session_id)
        return jsonify(response_data), 200

    except TimeoutError:
        return jsonify({
            "type":  "error",
            "reply": "Test timed out after 120 seconds. Please try again."
        }), 504

    except ConnectionError:
        return jsonify({
            "type":  "error",
            "reply": "Connection failed. The website might be down."
        }), 502

    except Exception as e:
        logger.error(f"Error: {str(e)[:200]}")
        return jsonify({
            "type":  "error",
            "reply": f"An error occurred: {str(e)[:150]}"
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


@app.route("/current-game", methods=["GET"])
def get_current_game():
    """
    Returns the last tested game info for the current session.
    Used by frontend to show game context in sidebar.
    """
    try:
        session_id = get_session_id()
        from chatbot import get_current_game_context
        game_context = get_current_game_context(session_id)
        return jsonify(game_context), 200
    except Exception as e:
        logger.error(f"Current game error: {e}")
        return jsonify({"game": None}), 200


# ── Error Handlers ────────────────────────────────────────────
@app.errorhandler(400)
def bad_request(e):
    return jsonify({"type": "error", "reply": "Bad request."}), 400


@app.errorhandler(404)
def not_found(e):
    return jsonify({"type": "error", "reply": "Not found."}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"type": "error", "reply": "Server error."}), 500


# ── Entry Point ───────────────────────────────────────────────
if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    logger.info(f"Starting TestProbe AI v3.0 on port {port}")
    app.run(
        debug=debug,
        port=port,
        host="0.0.0.0",
        threaded=True
    )

    print("Static folder path:", app.static_folder)
print("CSS exists:", os.path.exists(
    os.path.join(app.static_folder, 'css', 'style.css')
))

@app.route("/test-direct", methods=["POST"])
def test_direct_url():
    """
    DIRECT URL TESTING - Bypasses all extraction logic
    Use this if normal detection fails
    """
    data = request.get_json(silent=True)
    if not data or "url" not in data:
        return jsonify({"type": "error", "reply": "No URL provided"}), 400
    
    url = data["url"].strip()
    
    # Add https:// if missing
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    
    logger.info(f"DIRECT TEST - URL: {url}")
    
    from chatbot import run_game_test
    session_id = get_session_id()
    
    try:
        result = run_game_test(url, session_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Direct test error: {e}")
        return jsonify({"type": "error", "reply": str(e)}), 500