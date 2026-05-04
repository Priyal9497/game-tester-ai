"""
TestProbe AI - Chatbot Message Processor
"""

import re
import logging
from typing import Optional, List, Dict
from urllib.parse import urlparse
from datetime import datetime
from collections import deque

from tester import run_test
from ai_helper import get_ai_test_analysis, get_ai_game_conversation

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────
MAX_HISTORY      = 50
MAX_CONVERSATION = 20

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
    },
    "NotGame": {
        "emoji":   "❌",
        "comment": "This doesn't appear to be a playable game.",
        "tip":     "Please send a valid game URL."
    }
}

# ── Test History ──────────────────────────────────────────────
test_history: deque = deque(maxlen=MAX_HISTORY)

# ── Conversation Memory ───────────────────────────────────────
conversation_memory: Dict[str, List[Dict]] = {}


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
                "." in parsed.netloc or parsed.netloc == "localhost"
            ]):
                return url
        except Exception:
            continue
    return None


# ── Game Link Detection (Pre-test) ────────────────────────────
def is_likely_game_url(url: str) -> tuple:
    """
    Check if URL is likely a game link before loading
    Returns: (is_game, reason)
    """
    url_lower = url.lower()

    game_domains = [
        "chromedino.com", "chrome.com/dino", "pokemon",
        "miniclip", "kongregate", "newgrounds", "armorgames",
        "crazygames", "poki", "coolmathgames", "addictinggames",
        "nitrome", "agame", "friv", "y8.com", "gamepix",
        "html5games", "itch.io", "gameflare", "playhop",
        "steampowered", "epicgames", "roblox", "minecraft",
        "chess.com", "lichess.org", "tetris.com", "slither.io"
    ]

    game_indicators = [
        "/game/", "/play/", "/games/", "/arcade/",
        "game.html", "play.html", "index.html", "/gameplay"
    ]

    non_game_domains = [
        "google", "facebook", "twitter", "instagram", "youtube",
        "linkedin", "github", "stackoverflow", "reddit", "amazon",
        "flipkart", "ebay", "wikipedia", "quora", "medium",
        "netflix", "spotify", "gmail", "outlook", "yahoo",
        "whatsapp", "telegram", "discord", "tiktok", "snapchat"
    ]

    non_game_indicators = [
        "/watch?v=", "/shorts/", "/feed/", "/post/",
        "/article/", "/blog/", "/news/", "search?",
        "login", "signup", "register", "mail."
    ]

    for bad in non_game_domains:
        if bad in url_lower:
            return False, f"'{bad}' is not a gaming website"

    for bad in non_game_indicators:
        if bad in url_lower:
            return False, f"URL contains '{bad}' - not a game link"

    for good in game_domains:
        if good in url_lower:
            return True, "Game domain detected"

    for indicator in game_indicators:
        if indicator in url_lower:
            return True, "Game path detected"

    return None, "Requires page inspection"


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

    valid_perfs = ("High", "Medium", "Low", "NotGame")
    if metrics.get("performance") not in valid_perfs:
        return False, f"performance must be one of {valid_perfs}"

    if not isinstance(metrics.get("scores"), list):
        return False, "scores must be a list"

    return True, "OK"


# ── Reply Builder ─────────────────────────────────────────────
def build_reply(url: str, metrics: dict, ai_analysis: str) -> str:
    perf = metrics["performance"]

    if perf == "NotGame":
        reason = metrics.get("game_check_reason", "No game detected")
        return (
            f"❌ WRONG LINK - CANNOT TEST THIS\n\n"
            f"URL: {url}\n"
            f"{'─' * 40}\n"
            f"Reason: {reason}\n\n"
            f"This doesn't appear to be a playable web game.\n"
            f"Please send a valid game URL.\n\n"
            f"Examples:\n"
            f"  https://chromedino.com\n"
            f"  https://poki.com\n"
            f"  https://crazygames.com\n"
            f"{'─' * 40}"
        )

    time_s  = metrics["time_survived"]
    actions = metrics["actions"]
    errors  = metrics.get("errors", 0)
    config  = PERF_CONFIG.get(perf, PERF_CONFIG["Low"])
    aps     = round(actions / time_s, 2) if time_s > 0 else 0

    return (
        f"✅ TEST COMPLETE!\n"
        f"URL: {url}\n\n"
        f"{'─' * 40}\n"
        f"Time Survived  : {time_s:.1f} seconds\n"
        f"Actions Done   : {actions}\n"
        f"Actions/sec    : {aps}\n"
        f"Errors Found   : {errors}\n"
        f"Performance    : {config['emoji']} {perf}\n"
        f"{'─' * 40}\n\n"
        f"{config['comment']}\n"
        f"{config['tip']}\n\n"
        f"{'─' * 40}\n"
        f"AI ANALYSIS:\n\n"
        f"{ai_analysis}"
    )


# ── Conversation Memory Management ────────────────────────────
def add_to_conversation(session_id: str, role: str, content: str):
    if session_id not in conversation_memory:
        conversation_memory[session_id] = []

    conversation_memory[session_id].append({
        "role":      role,
        "content":   content,
        "timestamp": datetime.now().isoformat()
    })

    if len(conversation_memory[session_id]) > MAX_CONVERSATION:
        conversation_memory[session_id] = (
            conversation_memory[session_id][-MAX_CONVERSATION:]
        )


def get_conversation_context(session_id: str) -> List[Dict]:
    if session_id not in conversation_memory:
        return []
    return conversation_memory[session_id][-MAX_CONVERSATION:]


# ── Game Test Runner ──────────────────────────────────────────
def run_game_test(url: str, session_id: str = "default") -> dict:
    logger.info(f"Starting game test: {url}")

    is_game, reason = is_likely_game_url(url)

    if is_game is False:
        logger.info(f"Pre-check rejected: {reason}")

        not_game_metrics = {
            "time_survived":    0,
            "actions":          0,
            "performance":      "NotGame",
            "scores":           [0],
            "errors":           0,
            "screenshots":      [],
            "page_info":        {"title": "N/A", "has_canvas": False},
            "url":              url,
            "load_failed":      True,
            "not_a_game":       True,
            "game_check_reason": reason,
            "tested_at":        datetime.now().isoformat()
        }

        test_history.append({
            "url":       url,
            "metrics":   not_game_metrics,
            "ai_analysis": "Not a game link.",
            "success":   False,
            "not_a_game": True,
            "reason":    reason,
            "timestamp": datetime.now().isoformat()
        })

        add_to_conversation(session_id, "user", url)
        add_to_conversation(session_id, "assistant", f"Wrong link: {reason}")

        return {
            "type":        "test_result",
            "reply":       build_reply(url, not_game_metrics, "This URL does not appear to be a game."),
            "metrics":     not_game_metrics,
            "ai_analysis": "Not a game link."
        }

    try:
        logger.info("Running Selenium test...")
        metrics = run_test(url)

        is_valid, val_reason = validate_metrics(metrics)
        if not is_valid:
            raise ValueError(f"Invalid metrics: {val_reason}")

        ai_analysis = "AI analysis unavailable."
        if metrics.get("performance") != "NotGame":
            logger.info("Getting AI analysis from Groq...")
            ai_analysis = get_ai_test_analysis(url, metrics)
        else:
            ai_analysis = "This URL does not point to a valid game."

        reply = build_reply(url, metrics, ai_analysis)

        test_history.append({
            "url":         url,
            "metrics":     metrics,
            "ai_analysis": ai_analysis,
            "success":     metrics.get("performance") != "NotGame",
            "timestamp":   datetime.now().isoformat()
        })

        add_to_conversation(session_id, "user", url)
        add_to_conversation(session_id, "assistant", reply[:500])

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
def process_message(message: str, session_id: str = None) -> dict:
    if not message or not isinstance(message, str):
        return {
            "type":  "error",
            "reply": "Invalid message received."
        }

    if session_id is None:
        session_id = "default_session"

    logger.info(f"Processing: {message[:80]}")

    url = extract_url(message)

    if url:
        return run_game_test(url, session_id)

    logger.info("No URL found - having AI conversation")

    conversation_context = get_conversation_context(session_id)
    ai_reply = get_ai_game_conversation(message, conversation_context)

    add_to_conversation(session_id, "user", message)
    add_to_conversation(session_id, "assistant", ai_reply)

    return {
        "type":  "chat",
        "reply": ai_reply
    }


# ── Get History ───────────────────────────────────────────────
def get_test_history() -> list:
    return list(test_history)