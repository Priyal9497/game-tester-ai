"""
TestProbe AI - Chatbot Message Processor
"""

import re
import logging
from typing import Optional
from urllib.parse import urlparse
from datetime import datetime
from collections import deque

from tester import run_test
from ai_helper import get_ai_test_analysis, get_ai_chat_reply

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────
MAX_HISTORY      = 50
REQUIRED_METRICS = {
    "time_survived", "actions", "performance", "scores"
}

PERF_CONFIG = {
    "High": {
        "emoji":   "🟢",
        "comment": "Excellent! The game performed outstandingly.",
        "tip":     "No major issues detected."
    },
    "Medium": {
        "emoji":   "🟡",
        "comment": "Good performance with room for improvement.",
        "tip":     "Consider optimizing game load time."
    },
    "Low": {
        "emoji":   "🔴",
        "comment": "Poor performance detected.",
        "tip":     "Game may have stability or loading issues."
    }
}

# ── Test History ──────────────────────────────────────────────
test_history: deque = deque(maxlen=MAX_HISTORY)

# ── URL Extraction ────────────────────────────────────────────
def extract_url(text: str) -> Optional[str]:
    url_pattern = re.compile(
        r"https?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)"
        r"+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"
        r"localhost|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)",
        re.IGNORECASE
    )
    urls = url_pattern.findall(text)
    for url in urls:
        try:
            parsed = urlparse(url)
            if all([
                parsed.scheme in ("http", "https"),
                parsed.netloc,
                "." in parsed.netloc or
                parsed.netloc == "localhost"
            ]):
                return url
        except Exception:
            continue
    return None


# ── Metrics Validation ────────────────────────────────────────
def validate_metrics(metrics: dict) -> tuple:
    if not isinstance(metrics, dict):
        return False, "Metrics must be a dictionary"

    missing = REQUIRED_METRICS - set(metrics.keys())
    if missing:
        return False, f"Missing fields: {missing}"

    if not isinstance(metrics.get("time_survived"), (int, float)):
        return False, "time_survived must be a number"

    if not isinstance(metrics.get("actions"), int):
        return False, "actions must be an integer"

    if metrics.get("performance") not in ("High", "Medium", "Low"):
        return False, "performance must be High Medium or Low"

    if not isinstance(metrics.get("scores"), list):
        return False, "scores must be a list"

    return True, "OK"


# ── Reply Builder ─────────────────────────────────────────────
def build_reply(url: str, metrics: dict, ai_analysis: str) -> str:
    perf    = metrics["performance"]
    time_s  = metrics["time_survived"]
    actions = metrics["actions"]
    errors  = metrics.get("errors", 0)
    config  = PERF_CONFIG.get(perf, PERF_CONFIG["Low"])
    aps     = round(actions / time_s, 2) if time_s > 0 else 0

    return (
        f"Test Complete!\n"
        f"URL: {url}\n\n"
        f"{'─' * 35}\n"
        f"Time Survived  : {time_s:.1f} seconds\n"
        f"Actions Done   : {actions}\n"
        f"Actions/sec    : {aps}\n"
        f"Errors Found   : {errors}\n"
        f"Performance    : {config['emoji']} {perf}\n"
        f"{'─' * 35}\n\n"
        f"{config['comment']}\n"
        f"{config['tip']}\n\n"
        f"{'─' * 35}\n"
        f"AI Analysis:\n\n"
        f"{ai_analysis}"
    )


# ── Game Test Runner ──────────────────────────────────────────
def run_game_test(url: str) -> dict:
    logger.info(f"Starting game test: {url}")

    try:
        # ── Run Selenium Test ──
        logger.info("Running Selenium test...")
        metrics = run_test(url)

        # ── Validate Metrics ──
        is_valid, reason = validate_metrics(metrics)
        if not is_valid:
            raise ValueError(f"Invalid metrics: {reason}")

        # ── Get Groq AI Analysis ──
        logger.info("Getting AI analysis from Groq...")
        ai_analysis = get_ai_test_analysis(url, metrics)

        # ── Build Reply ──
        reply = build_reply(url, metrics, ai_analysis)

        # ── Save to History ──
        test_history.append({
            "url":         url,
            "metrics":     metrics,
            "ai_analysis": ai_analysis,
            "success":     True,
            "timestamp":   datetime.now().isoformat()
        })

        logger.info("Test completed successfully")

        return {
            "type":        "test_result",
            "reply":       reply,
            "metrics":     metrics,
            "ai_analysis": ai_analysis
        }

    except TimeoutError:
        logger.error(f"Timeout for: {url}")
        test_history.append({
            "url":       url,
            "success":   False,
            "error":     "timeout",
            "timestamp": datetime.now().isoformat()
        })
        raise

    except ConnectionError:
        logger.error(f"Connection error for: {url}")
        test_history.append({
            "url":       url,
            "success":   False,
            "error":     "connection",
            "timestamp": datetime.now().isoformat()
        })
        raise

    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        test_history.append({
            "url":       url,
            "success":   False,
            "error":     str(e),
            "timestamp": datetime.now().isoformat()
        })
        raise


# ── Main Entry Point ──────────────────────────────────────────
def process_message(message: str) -> dict:
    if not message or not isinstance(message, str):
        return {
            "type":  "error",
            "reply": "Invalid message received."
        }

    logger.info(f"Processing: {message[:80]}")

    # ── Check for URL first ──
    url = extract_url(message)

    if url:
        return run_game_test(url)

    # ── No URL found - use Groq for chat ──
    logger.info("No URL found - using Groq for chat reply")
    ai_reply = get_ai_chat_reply(message)

    return {
        "type":  "info",
        "reply": ai_reply
    }


# ── History Access ────────────────────────────────────────────
def get_test_history() -> list:
    return list(test_history)