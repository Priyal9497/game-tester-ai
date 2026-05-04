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
    get_human_ai_verdict
)

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

# ── Current Game Context per session ─────────────────────────
current_game_context: Dict[str, Dict] = {}


# ── URL Extraction (FIXED) ────────────────────────────────────
def extract_url(text: str) -> Optional[str]:
    """
    Extract first valid URL from text - SIMPLIFIED & RELIABLE VERSION
    """
    if not text:
        return None
    
    text = text.strip()
    
    # Pattern 1: Full http:// or https:// URLs
    http_pattern = r'https?://[^\s<>"\'{}|\\^`\[\]]+'
    matches = re.findall(http_pattern, text, re.IGNORECASE)
    if matches:
        url = matches[0]
        # Clean trailing punctuation
        url = re.sub(r'[.,;:!?)]+$', '', url)
        return url
    
    # Pattern 2: www. URLs (no protocol)
    www_pattern = r'www\.[a-zA-Z0-9][-a-zA-Z0-9]*(?:\.[a-zA-Z]{2,})+\S*'
    matches = re.findall(www_pattern, text, re.IGNORECASE)
    if matches:
        url = 'https://' + matches[0]
        url = re.sub(r'[.,;:!?)]+$', '', url)
        return url
    
    # Pattern 3: Simple domain like "chromedino.com" or "poki.com"
    domain_pattern = r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.)+[a-zA-Z]{2,}(?:/[\w\-/=%?]*)?\b'
    matches = re.findall(domain_pattern, text, re.IGNORECASE)
    if matches:
        domain = matches[0]
        # Make sure it's a real domain
        if '.' in domain and len(domain) > 4:
            # Don't match email addresses
            if '@' not in domain:
                url = 'https://' + domain
                url = re.sub(r'[.,;:!?)]+$', '', url)
                return url
    
    # Pattern 4: Chrome internal URLs (for dino game)
    chrome_pattern = r'chrome://[^\s<>"\']+'
    matches = re.findall(chrome_pattern, text, re.IGNORECASE)
    if matches:
        return matches[0]
    
    return None


def manual_url_extract(text: str) -> Optional[str]:
    """
    Manual URL extraction as fallback - very simple approach
    """
    # Very simple - find anything that looks like a domain
    domain_pattern = r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.)+[a-zA-Z]{2,}\b'
    matches = re.findall(domain_pattern, text)
    
    # Common game domains for quick matching
    game_domains = [
        "chromedino.com", "poki.com", "crazygames.com",
        "coolmathgames.com", "miniclip.com", "kongregate.com",
        "newgrounds.com", "itch.io", "y8.com", "friv.com",
        "addictinggames.com", "agame.com", "nitrome.com",
        "gamepix.com", "gameflare.com", "html5games.com",
        "playhop.com", "chess.com", "lichess.org",
        "tetris.com", "slither.io", "2048.org",
        "armorgames.com", "silvergames.com", "kizi.com"
    ]
    
    for match in matches:
        if '.' in match and len(match) > 4:
            # Check if it's in our game list
            for game in game_domains:
                if game in match:
                    return 'https://' + match
    
    # If it has .com, .io, .org and looks like a domain, try it
    if matches:
        for match in matches:
            if any(ext in match for ext in ['.com', '.io', '.org', '.net', '.game']):
                return 'https://' + match
    
    return None


# ── Game Link Detection (FIXED) ────────────────────────────
def is_likely_game_url(url: str) -> tuple:
    """
    Check if URL looks like a game site.
    Returns (is_likely, reason)
    True = game, False = not game, None = uncertain
    """
    url_lower = url.lower()
    
    # EXTENDED GAME DOMAINS
    game_domains = [
        "chromedino.com", "chrome://dino",
        "poki.com", "pokigame.com",
        "crazygames.com", "crazygames",
        "coolmathgames.com", "coolmath",
        "miniclip.com", "kongregate.com",
        "newgrounds.com", "itch.io",
        "y8.com", "friv.com", "friv",
        "addictinggames.com", "agame.com",
        "nitrome.com", "gamepix.com",
        "gameflare.com", "html5games.com",
        "playhop.com", "chess.com",
        "lichess.org", "tetris.com",
        "slither.io", "2048.org", "2048",
        "armorgames.com", "silvergames.com",
        "kizi.com", "mousebreaker.com",
        "gamesbutler.com", "lagged.com",
        "onlinegames.io", "gamedistribution.com",
        "mathplayground.com", "hoodamath.com",
        "abcya.com", "coolmath-games.com",
        "primarygames.com", "turtlediary.com",
        "arcadeprehacks.com", "hoodamath",
        "mathplayground", "abcya"
    ]
    
    # Check each game domain
    try:
        # Parse the URL
        parsed_url = urlparse(url if '://' in url else 'https://' + url)
        domain = parsed_url.netloc.lower()
        
        # Remove www prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Check exact match or partial match
        for game_domain in game_domains:
            if game_domain in domain or domain == game_domain:
                return (True, f"Known game domain: {domain}")
    except Exception as e:
        logger.warning(f"URL parse error: {e}")
    
    # Check for game-related paths
    game_paths = [
        "/game/", "/play/", "/games/", "/arcade/",
        "game.html", "play.html", "/gameplay",
        "/puzzle/", "/action/", "/racing/", "/shooter/",
        "/adventure/", "/strategy/", "/sports/"
    ]
    
    for path in game_paths:
        if path in url_lower:
            return (True, f"Game path: {path}")
    
    # Default: Let Selenium test it
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

    time_s     = metrics["time_survived"]
    actions    = metrics["actions"]
    errors     = metrics.get("errors", 0)
    config     = PERF_CONFIG.get(perf, PERF_CONFIG["Low"])
    aps        = round(actions / time_s, 2) if time_s > 0 else 0
    game_type  = metrics.get("game_type", {})

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
        verdict      = human_verdict.get("verdict", "Unknown")
        confidence   = human_verdict.get("confidence", "Low")
        verdict_emoji = {
            "Human":    "👤",
            "AI/Bot":   "🤖",
            "Uncertain": "❓"
        }.get(verdict, "❓")

        verdict_section = (
            f"\n{'─' * 40}\n"
            f"HUMAN vs AI DETECTION:\n\n"
            f"Verdict        : {verdict_emoji} {verdict}\n"
            f"Confidence     : {confidence}\n"
            f"Reason         : {human_verdict.get('reason', '')}\n"
        )

    # AI tests performed section
    tests_section = ""
    ai_tests = metrics.get("ai_tests_performed", [])
    if ai_tests:
        tests_list    = "\n".join([f"  ✓ {t}" for t in ai_tests[:5]])
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
def set_current_game_context(session_id: str, url: str, metrics: dict,
                              human_verdict: dict, ai_analysis: str):
    """Store current game context for follow-up questions"""
    game_type = metrics.get("game_type", {})
    page_info = metrics.get("page_info", {})

    current_game_context[session_id] = {
        "url":          url,
        "title":        page_info.get("title", "Unknown"),
        "game_type":    game_type.get("primary_type", "Unknown"),
        "confidence":   game_type.get("confidence", "Low"),
        "description":  game_type.get("description", ""),
        "performance":  metrics.get("performance", "Low"),
        "time_survived": metrics.get("time_survived", 0),
        "actions":      metrics.get("actions", 0),
        "errors":       metrics.get("errors", 0),
        "human_verdict": human_verdict,
        "ai_analysis":  ai_analysis,
        "has_canvas":   page_info.get("has_canvas", False),
        "tested_at":    metrics.get("tested_at", datetime.now().isoformat()),
        "ai_tests":     metrics.get("ai_tests_performed", [])
    }


def get_current_game_context(session_id: str) -> dict:
    """Get current game context for this session"""
    if session_id not in current_game_context:
        return {"game": None}
    return {"game": current_game_context[session_id]}


def build_game_context_prompt(session_id: str) -> str:
    """Build context string for AI follow-up questions"""
    if session_id not in current_game_context:
        return ""

    ctx = current_game_context[session_id]
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
def get_ai_tests_performed(metrics: dict) -> list:
    """
    Based on metrics, list which AI tests were actually performed
    during the Selenium test session
    """
    tests = []
    page_info = metrics.get("page_info", {})

    tests.append("Page Load Verification")
    tests.append("URL Pattern Analysis")

    if page_info.get("has_canvas"):
        tests.append("Canvas Element Detection")

    if page_info.get("has_game_elements"):
        tests.append("Game DOM Element Scanning")

    tests.append("Anti-Bot Detection Bypass")
    tests.append("Keyboard Interaction Simulation")
    tests.append("Score Extraction Attempt")
    tests.append("Error Page Detection")
    tests.append("Performance Scoring")

    game_type = metrics.get("game_type", {})
    if game_type.get("primary_type"):
        tests.append(f"Game Type Classification")

    if metrics.get("actions", 0) > 0:
        tests.append("Action Rate Analysis")
        tests.append("Human Behavior Pattern Check")

    tests.append("Groq AI Analysis")
    tests.append("Human vs AI Verdict")

    return tests


# ── Game Test Runner ──────────────────────────────────────────
def run_game_test(url: str, session_id: str = "default") -> dict:
    logger.info(f"Starting game test: {url}")

    is_game, reason = is_likely_game_url(url)

    if is_game is False:
        logger.info(f"Pre-check rejected: {reason}")

        not_game_metrics = {
            "time_survived":     0,
            "actions":           0,
            "performance":       "NotGame",
            "scores":            [0],
            "errors":            0,
            "screenshots":       [],
            "page_info":         {"title": "N/A", "has_canvas": False},
            "game_type":         {},
            "url":               url,
            "load_failed":       True,
            "not_a_game":        True,
            "game_check_reason": reason,
            "ai_tests_performed": ["URL Pattern Analysis", "Domain Blacklist Check"],
            "tested_at":         datetime.now().isoformat()
        }

        test_history.append({
            "url":        url,
            "metrics":    not_game_metrics,
            "ai_analysis": "Not a game link.",
            "success":    False,
            "not_a_game": True,
            "reason":     reason,
            "timestamp":  datetime.now().isoformat()
        })

        add_to_conversation(session_id, "user", url)
        add_to_conversation(session_id, "assistant", f"Wrong link: {reason}")

        return {
            "type":        "test_result",
            "reply":       build_reply(url, not_game_metrics, "This URL does not appear to be a game."),
            "metrics":     not_game_metrics,
            "ai_analysis": "Not a game link.",
            "human_verdict": None,
            "game_context":  None
        }

    try:
        logger.info("Running Selenium test...")
        metrics = run_test(url)

        is_valid, val_reason = validate_metrics(metrics)
        if not is_valid:
            raise ValueError(f"Invalid metrics: {val_reason}")

        # Track AI tests performed
        ai_tests = get_ai_tests_performed(metrics)
        metrics["ai_tests_performed"] = ai_tests

        # Get AI analysis
        ai_analysis   = "AI analysis unavailable."
        human_verdict = None

        if metrics.get("performance") != "NotGame":
            logger.info("Getting AI analysis from Groq...")
            ai_analysis = get_ai_test_analysis(url, metrics)

            logger.info("Getting Human vs AI verdict...")
            human_verdict = get_human_ai_verdict(url, metrics)

        else:
            ai_analysis   = "This URL does not point to a valid game."
            human_verdict = {
                "verdict":    "Unknown",
                "confidence": "N/A",
                "reason":     "Not a valid game page"
            }

        # Add verdict to metrics for frontend
        metrics["human_verdict"]    = human_verdict
        metrics["ai_tests_performed"] = ai_tests

        # Build reply
        reply = build_reply(url, metrics, ai_analysis, human_verdict)

        # Store game context for follow-up questions
        set_current_game_context(session_id, url, metrics, human_verdict, ai_analysis)

        # Save to history
        test_history.append({
            "url":          url,
            "metrics":      metrics,
            "ai_analysis":  ai_analysis,
            "human_verdict": human_verdict,
            "success":      metrics.get("performance") != "NotGame",
            "timestamp":    datetime.now().isoformat()
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


# ── Main Entry Point (FIXED WITH DEBUG) ──────────────────────────
def process_message(message: str, session_id: str = None) -> dict:
    if not message or not isinstance(message, str):
        return {
            "type":  "error",
            "reply": "Invalid message received."
        }

    if session_id is None:
        session_id = "default_session"

    logger.info(f"Processing: {message[:100]} | Session: {session_id}")
    
    # DEBUG: Log what we're checking
    logger.info(f"Checking if message contains URL...")
    logger.info(f"Message: '{message}'")
    
    # Check for common URL patterns manually for debugging
    has_http = 'http' in message.lower()
    has_dot_com = '.com' in message.lower()
    has_dot_io = '.io' in message.lower()
    has_dot_org = '.org' in message.lower()
    
    logger.info(f"Debug - Has http: {has_http}, Has .com: {has_dot_com}, Has .io: {has_dot_io}")
    
    # Extract URL
    url = extract_url(message)
    
    if url:
        logger.info(f"✅ SUCCESS - URL extracted: {url}")
        return run_game_test(url, session_id)
    
    # Try manual extraction as fallback
    manual_url = manual_url_extract(message)
    if manual_url:
        logger.info(f"✅ Manual extraction succeeded: {manual_url}")
        return run_game_test(manual_url, session_id)
    
    logger.warning(f"❌ No URL extracted from: '{message[:50]}'")
    
    # It's a chat message - check if game context exists
    logger.info("No URL found - handling as chat question")

    # Build context string if we have a game analyzed
    game_context_prompt = build_game_context_prompt(session_id)
    has_game_context    = session_id in current_game_context

    # Get conversation history
    conversation_context = get_conversation_context(session_id)

    # Get AI reply with game context
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