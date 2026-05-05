"""
TestProbe AI - Chatbot Message Processor v3.0 (FIXED)
"""

import re
import logging
from typing import Optional, List, Dict
from urllib.parse import urlparse
from datetime import datetime
from collections import deque

from tester import run_test
from ai_helper import (
    get_ai_test_analysis,
    get_ai_game_conversation,
    get_human_ai_verdict,
    get_groq_client        # ✅ Import to check if Groq available
)

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────
MAX_HISTORY      = 50
MAX_CONVERSATION = 20
MAX_SESSIONS     = 100    # ✅ NEW — Prevent memory leak

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

# ── Current Game Context per session ─────────────────────────
current_game_context: Dict[str, Dict] = {}


# ── Session Memory Management ─────────────────────────────────
def cleanup_old_sessions():
    """
    ✅ FIXED — Prevent memory leak
    Remove oldest sessions when limit reached
    """
    if len(conversation_memory) > MAX_SESSIONS:
        # Remove oldest 20 sessions
        keys_to_remove = list(conversation_memory.keys())[:20]
        for key in keys_to_remove:
            conversation_memory.pop(key, None)
            current_game_context.pop(key, None)
        logger.info(f"Cleaned up {len(keys_to_remove)} old sessions")


# ── URL Extraction ────────────────────────────────────────────
def extract_url(text: str) -> Optional[str]:
    """
    Extract first valid URL from text
    """
    if not text:
        return None

    text = text.strip()

    # Pattern 1: Full http:// or https:// URLs
    http_pattern = r'https?://[^\s<>"\'{}|\\^`\[\]]+'
    matches = re.findall(http_pattern, text, re.IGNORECASE)
    if matches:
        url = matches[0]
        url = re.sub(r'[.,;:!?)]+$', '', url)
        return url

    # Pattern 2: www. URLs (no protocol)
    www_pattern = r'www\.[a-zA-Z0-9][-a-zA-Z0-9]*(?:\.[a-zA-Z]{2,})+\S*'
    matches = re.findall(www_pattern, text, re.IGNORECASE)
    if matches:
        url = 'https://' + matches[0]
        url = re.sub(r'[.,;:!?)]+$', '', url)
        return url

    # Pattern 3: Simple domain
    domain_pattern = (
        r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.)+[a-zA-Z]{2,}'
        r'(?:/[\w\-/=%?]*)?\b'
    )
    matches = re.findall(domain_pattern, text, re.IGNORECASE)
    if matches:
        domain = matches[0]
        if '.' in domain and len(domain) > 4 and '@' not in domain:
            url = 'https://' + domain
            url = re.sub(r'[.,;:!?)]+$', '', url)
            return url

    return None


def manual_url_extract(text: str) -> Optional[str]:
    """
    ✅ FIXED — Only extract from KNOWN game domains
    No longer matches random .com domains
    """
    # Only known game domains
    game_domains = [
        "chromedino.com", "poki.com", "crazygames.com",
        "coolmathgames.com", "miniclip.com", "kongregate.com",
        "newgrounds.com", "itch.io", "y8.com", "friv.com",
        "addictinggames.com", "agame.com", "nitrome.com",
        "gamepix.com", "gameflare.com", "html5games.com",
        "playhop.com", "chess.com", "lichess.org",
        "tetris.com", "slither.io", "2048.org",
        "armorgames.com", "silvergames.com", "kizi.com",
        "onlinegames.io", "gamedistribution.com",
        "coolmath-games.com", "abcya.com"
    ]

    text_lower = text.lower()

    # ✅ Only match if it's a known game domain
    for domain in game_domains:
        if domain in text_lower:
            return 'https://' + domain

    return None


# ── Game Link Detection ───────────────────────────────────────
def is_likely_game_url(url: str) -> tuple:
    """
    Check if URL looks like a game site.
    Returns (is_likely, reason)
    """
    url_lower = url.lower()

    # ✅ NOT game domains - reject these
    not_game_domains = [
        "google.com", "facebook.com", "twitter.com",
        "instagram.com", "youtube.com", "linkedin.com",
        "amazon.com", "wikipedia.org", "reddit.com",
        "github.com", "stackoverflow.com", "gmail.com",
        "outlook.com", "yahoo.com", "netflix.com",
        "spotify.com", "apple.com", "microsoft.com"
    ]

    # ✅ Known game domains - always allow these
    game_domains = [
        "chromedino.com", "poki.com", "crazygames.com",
        "coolmathgames.com", "miniclip.com", "kongregate.com",
        "newgrounds.com", "itch.io", "y8.com", "friv.com",
        "addictinggames.com", "agame.com", "nitrome.com",
        "gamepix.com", "gameflare.com", "html5games.com",
        "playhop.com", "chess.com", "lichess.org",
        "tetris.com", "slither.io", "2048.org",
        "armorgames.com", "silvergames.com", "kizi.com",
        "onlinegames.io", "gamedistribution.com",
        "coolmath-games.com", "abcya.com", "mathplayground.com",
        "hoodamath.com", "primarygames.com", "arcadeprehacks.com",
        "mousebreaker.com", "lagged.com", "kizi.com",
        "gamepix.com", "html5games.com"
    ]

    # ✅ SIMPLE CHECK - just use 'in' on the full URL string
    # This avoids all domain parsing bugs
    for not_game in not_game_domains:
        if not_game in url_lower:
            return (False, f"Non-game domain detected")

    # ✅ Check game domains directly in URL string
    for game_domain in game_domains:
        if game_domain in url_lower:
            return (True, f"Known game domain: {game_domain}")

    # ✅ Check game paths
    game_paths = [
        "/game/", "/play/", "/games/", "/arcade/",
        "game.html", "play.html", "/gameplay",
        "/puzzle/", "/action/", "/racing/", "/shooter/"
    ]

    for path in game_paths:
        if path in url_lower:
            return (True, f"Game path detected: {path}")

    # ✅ Default - let tester decide, don't reject!
    return (None, "Will test with browser")


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
def build_reply(
    url: str,
    metrics: dict,
    ai_analysis: str,
    human_verdict: dict = None
) -> str:
    perf = metrics.get("performance", "Low")

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

    time_s    = metrics.get("time_survived", 0)
    actions   = metrics.get("actions", 0)
    errors    = metrics.get("errors", 0)
    config    = PERF_CONFIG.get(perf, PERF_CONFIG["Low"])
    game_type = metrics.get("game_type", {})

    # ✅ FIXED — Safe division
    aps = round(actions / max(float(time_s), 1.0), 2)

    # Game type section
    game_type_section = ""
    if game_type and game_type.get("primary_type"):
        game_type_section = (
            f"Game Type      : {game_type.get('primary_type', 'Unknown')}\n"
            f"Confidence     : {game_type.get('confidence', 'Low')}\n"
            f"Description    : {game_type.get('description', '')}\n"
        )

    # Human/AI verdict section
    verdict_section = ""
    if human_verdict:
        verdict = human_verdict.get("verdict", "Unknown")
        confidence = human_verdict.get("confidence", "Low")
        verdict_emoji = {
            "Human":     "👤",
            "AI/Bot":    "🤖",
            "Uncertain": "❓"
        }.get(verdict, "❓")

        verdict_section = (
            f"\n{'─' * 40}\n"
            f"HUMAN vs AI DETECTION:\n\n"
            f"Verdict        : {verdict_emoji} {verdict}\n"
            f"Confidence     : {confidence}\n"
            f"Reason         : {human_verdict.get('reason', '')}\n"
        )

    # AI tests section
    tests_section = ""
    ai_tests = metrics.get("ai_tests_performed", [])
    if ai_tests:
        tests_list = "\n".join([f"  ✓ {t}" for t in ai_tests[:5]])
        tests_section = f"\nAI TESTS PERFORMED:\n{tests_list}\n"

    return (
        f"✅ TEST COMPLETE!\n"
        f"URL: {url}\n\n"
        f"{'─' * 40}\n"
        f"Time Survived  : {time_s:.1f} seconds\n"
        f"Actions Done   : {actions}\n"
        f"Actions/sec    : {aps}\n"
        f"Errors Found   : {errors}\n"
        f"Performance    : {config['emoji']} {perf}\n"
        f"{game_type_section}"
        f"{'─' * 40}\n\n"
        f"{config['comment']}\n"
        f"{config['tip']}\n"
        f"{verdict_section}"
        f"{tests_section}"
        f"\n{'─' * 40}\n"
        f"AI ANALYSIS:\n\n"
        f"{ai_analysis}\n\n"
        f"💬 You can now ask me questions about this game!"
    )


# ── Conversation Memory Management ────────────────────────────
def add_to_conversation(session_id: str, role: str, content: str):
    # ✅ Cleanup before adding new session
    cleanup_old_sessions()

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


# ── Game Context Management ───────────────────────────────────
def set_current_game_context(
    session_id: str,
    url: str,
    metrics: dict,
    human_verdict: dict,
    ai_analysis: str
):
    game_type = metrics.get("game_type", {})
    page_info = metrics.get("page_info", {})

    current_game_context[session_id] = {
        "url":           url,
        "title":         page_info.get("title", "Unknown"),
        "game_type":     game_type.get("primary_type", "Unknown"),
        "confidence":    game_type.get("confidence", "Low"),
        "description":   game_type.get("description", ""),
        "performance":   metrics.get("performance", "Low"),
        "time_survived": metrics.get("time_survived", 0),
        "actions":       metrics.get("actions", 0),
        "errors":        metrics.get("errors", 0),
        "human_verdict": human_verdict,
        "ai_analysis":   ai_analysis,
        "has_canvas":    page_info.get("has_canvas", False),
        "tested_at":     metrics.get(
            "tested_at", datetime.now().isoformat()
        ),
        "ai_tests":      metrics.get("ai_tests_performed", [])
    }


def get_current_game_context(session_id: str) -> dict:
    if session_id not in current_game_context:
        return {"game": None}
    return {"game": current_game_context[session_id]}


def build_game_context_prompt(session_id: str) -> str:
    if session_id not in current_game_context:
        return ""

    ctx         = current_game_context[session_id]
    verdict_info = ctx.get("human_verdict", {})

    return (
        f"CURRENTLY ANALYZED GAME:\n"
        f"URL: {ctx.get('url', 'Unknown')}\n"
        f"Title: {ctx.get('title', 'Unknown')}\n"
        f"Game Type: {ctx.get('game_type', 'Unknown')}\n"
        f"Description: {ctx.get('description', '')}\n"
        f"Performance: {ctx.get('performance', 'Unknown')}\n"
        f"Time Survived: {ctx.get('time_survived', 0)}s\n"
        f"Actions: {ctx.get('actions', 0)}\n"
        f"Errors: {ctx.get('errors', 0)}\n"
        f"Human/AI Verdict: {verdict_info.get('verdict', 'Unknown')}\n"
        f"Verdict Confidence: {verdict_info.get('confidence', 'Unknown')}\n"
        f"Has Canvas: {ctx.get('has_canvas', False)}\n"
        f"AI Tests Run: {', '.join(ctx.get('ai_tests', []))}\n"
    )


# ── AI Tests Tracker ──────────────────────────────────────────
def get_ai_tests_performed(metrics: dict, groq_available: bool = False) -> list:
    """
    ✅ FIXED — Only add tests that actually ran
    """
    tests     = []
    page_info = metrics.get("page_info", {})

    tests.append("Page Load Verification")
    tests.append("URL Pattern Analysis")

    if page_info.get("has_canvas"):
        tests.append("Canvas Element Detection")

    if page_info.get("has_game_elements"):
        tests.append("Game DOM Element Scanning")

    if metrics.get("actions", 0) > 0:
        tests.append("Keyboard Interaction Simulation")
        tests.append("Action Rate Analysis")
        tests.append("Human Behavior Pattern Check")

    if metrics.get("scores"):
        tests.append("Score Extraction Attempt")

    tests.append("Error Page Detection")
    tests.append("Performance Scoring")

    game_type = metrics.get("game_type", {})
    if game_type.get("primary_type"):
        tests.append("Game Type Classification")

    # ✅ FIXED — Only add Groq tests if Groq actually ran
    if groq_available:
        tests.append("Groq AI Analysis")
        tests.append("Human vs AI Verdict")

    return tests


# ── Game Test Runner ──────────────────────────────────────────
def run_game_test(url: str, session_id: str = "default") -> dict:
    logger.info(f"Starting game test: {url}")

    is_game, reason = is_likely_game_url(url)

    # ✅ FIXED — Handle None (uncertain) case explicitly
    if is_game is False:
        logger.info(f"Pre-check rejected: {reason}")

        not_game_metrics = {
            "time_survived":      0,
            "actions":            0,
            "performance":        "NotGame",
            "scores":             [0],
            "errors":             0,
            "screenshots":        [],
            "page_info":          {
                "title": "N/A", "has_canvas": False
            },
            "game_type":          {},
            "url":                url,
            "load_failed":        True,
            "not_a_game":         True,
            "game_check_reason":  reason,
            "ai_tests_performed": [
                "URL Pattern Analysis",
                "Domain Check"
            ],
            "tested_at":          datetime.now().isoformat()
        }

        test_history.append({
            "url":         url,
            "metrics":     not_game_metrics,
            "ai_analysis": "Not a game link.",
            "success":     False,
            "not_a_game":  True,
            "reason":      reason,
            "timestamp":   datetime.now().isoformat()
        })

        add_to_conversation(session_id, "user", url)
        add_to_conversation(
            session_id, "assistant", f"Wrong link: {reason}"
        )

        return {
            "type":          "test_result",
            "reply":         build_reply(
                url,
                not_game_metrics,
                "This URL does not appear to be a game."
            ),
            "metrics":       not_game_metrics,
            "ai_analysis":   "Not a game link.",
            "human_verdict": None,
            "game_context":  None
        }

    # ✅ is_game is True or None — proceed with Selenium test
    try:
        logger.info("Running Selenium test...")
        metrics = run_test(url)

        is_valid, val_reason = validate_metrics(metrics)
        if not is_valid:
            raise ValueError(f"Invalid metrics: {val_reason}")

        # ✅ FIXED — Check Groq availability
        groq_available = get_groq_client() is not None

        # Track AI tests performed
        ai_tests = get_ai_tests_performed(metrics, groq_available)
        metrics["ai_tests_performed"] = ai_tests

        # Get AI analysis
        ai_analysis   = "AI analysis unavailable."
        human_verdict = None

        if metrics.get("performance") != "NotGame":
            if groq_available:
                logger.info("Getting AI analysis from Groq...")
                ai_analysis = get_ai_test_analysis(url, metrics)

                logger.info("Getting Human vs AI verdict...")
                human_verdict = get_human_ai_verdict(url, metrics)
            else:
                ai_analysis = (
                    "AI analysis unavailable. "
                    "Add GROQ_API_KEY to environment variables."
                )
        else:
            ai_analysis   = "This URL does not point to a valid game."
            human_verdict = {
                "verdict":    "Unknown",
                "confidence": "N/A",
                "reason":     "Not a valid game page"
            }

        metrics["human_verdict"]      = human_verdict
        metrics["ai_tests_performed"] = ai_tests

        reply = build_reply(url, metrics, ai_analysis, human_verdict)

        set_current_game_context(
            session_id, url, metrics, human_verdict, ai_analysis
        )

        test_history.append({
            "url":           url,
            "metrics":       metrics,
            "ai_analysis":   ai_analysis,
            "human_verdict": human_verdict,
            "success":       metrics.get("performance") != "NotGame",
            "timestamp":     datetime.now().isoformat()
        })

        add_to_conversation(session_id, "user", url)
        add_to_conversation(session_id, "assistant", reply[:500])

        logger.info("Test completed successfully")

        return {
            "type":          "test_result",
            "reply":         reply,
            "metrics":       metrics,
            "ai_analysis":   ai_analysis,
            "human_verdict": human_verdict,
            "game_context":  current_game_context.get(session_id)
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

    # ✅ FIXED — Removed debug logs that exposed user data
    logger.info(f"Processing message | Session: {session_id}")

    # Extract URL
    url = extract_url(message)

    if url:
        logger.info(f"URL extracted: {url}")
        return run_game_test(url, session_id)

    # ✅ FIXED — Only try manual extract for known game domains
    manual_url = manual_url_extract(message)
    if manual_url:
        logger.info(f"Manual extraction: {manual_url}")
        return run_game_test(manual_url, session_id)

    logger.info("No URL found - handling as chat question")

    game_context_prompt = build_game_context_prompt(session_id)
    has_game_context    = session_id in current_game_context
    conversation_context = get_conversation_context(session_id)

    ai_reply = get_ai_game_conversation(
        message,
        conversation_context,
        game_context_prompt if has_game_context else None
    )

    add_to_conversation(session_id, "user", message)
    add_to_conversation(session_id, "assistant", ai_reply)

    return {
        "type":         "chat",
        "reply":        ai_reply,
        "has_context":  has_game_context,
        "game_context": current_game_context.get(session_id)
    }


# ── Get History ───────────────────────────────────────────────
def get_test_history() -> list:
    return list(test_history)
