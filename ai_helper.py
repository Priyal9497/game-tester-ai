"""
TestProbe AI - Groq AI Analysis Helper v3.0
"""

import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

# ── Initialize Groq Client ────────────────────────────────────
model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")


def get_groq_client():
    """
    ✅ FIXED — Lazy initialization
    Always tries to get fresh API key
    No more stuck None client
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not found in environment")
        return None
    try:
        client = Groq(api_key=api_key)
        return client
    except Exception as e:
        logger.error(f"Groq init failed: {e}")
        return None


# ── AI Test Analysis ──────────────────────────────────────────
def get_ai_test_analysis(url: str, metrics: dict) -> str:
    """
    Generate AI analysis of Selenium test results using Groq
    """
    # ✅ FIXED — Fresh client every time
    client = get_groq_client()

    if client is None:
        return (
            "AI analysis unavailable. "
            "Add GROQ_API_KEY to your environment variables."
        )

    page_info      = metrics.get("page_info", {})
    time_s         = metrics.get("time_survived", 0)
    actions        = metrics.get("actions", 0)
    errors         = metrics.get("errors", 0)
    performance    = metrics.get("performance", "Low")
    has_canvas     = page_info.get("has_canvas", False)
    has_game       = page_info.get("has_game_elements", False)
    page_title     = page_info.get("title", "Unknown")
    load_failed    = metrics.get("load_failed", False)
    game_type      = metrics.get("game_type", {})
    game_type_name = game_type.get("primary_type", "Unknown")
    ai_tests       = metrics.get("ai_tests_performed", [])

    if load_failed:
        return (
            "VERDICT: No\n"
            "ASSESSMENT: The page failed to load or render game elements.\n"
            "ISSUES: Selenium could not access or detect playable content.\n"
            "SUGGESTION: Check for anti-bot protection, iframe embedding, "
            "or JS-heavy lazy loading.\n"
            "NEXT STEP: Test manually in a regular browser, "
            "then retry with updated wait strategies."
        )

    prompt = f"""
You are an expert browser game QA testing assistant.

Analyze this automated Selenium test result and provide insights.

TEST DETAILS:
- URL: {url}
- Page Title: {page_title}
- Load Failed: {load_failed}
- Time Survived: {time_s} seconds
- Actions Performed: {actions}
- Errors Found: {errors}
- Performance Rating: {performance}
- Canvas Detected: {has_canvas}
- Game Elements Found: {has_game}
- Detected Game Type: {game_type_name}
- AI Tests Performed: {', '.join(ai_tests) if ai_tests else 'Standard tests'}

Based on these results provide:

1. VERDICT: Is this a valid playable game? (Yes/No/Uncertain)
2. ASSESSMENT: One sentence overall assessment
3. GAME TYPE NOTES: Brief comment on the detected game type
4. ISSUES: Main problem found if any
5. SUGGESTION: One specific improvement suggestion
6. NEXT STEP: What should tester do next

Keep each point to 1-2 sentences maximum.
Be direct and practical.
Do not use markdown or special formatting.
"""

    try:
        logger.info("Requesting Groq AI analysis...")
        completion = client.chat.completions.create(
            model=model,
            temperature=0.3,
            max_tokens=350,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a concise game QA testing assistant. "
                        "Give short practical actionable analysis. "
                        "Never use markdown formatting."
                    )
                },
                {
                    "role":    "user",
                    "content": prompt
                }
            ]
        )
        analysis = completion.choices[0].message.content.strip()
        logger.info("Groq analysis received successfully")
        return analysis

    except Exception as e:
        logger.error(f"Groq API error: {str(e)[:100]}")
        return f"AI analysis failed: {str(e)[:80]}"


# ── Human vs AI Verdict ───────────────────────────────────────
def get_human_ai_verdict(url: str, metrics: dict) -> dict:
    """
    Determine if the game session shows human-like or AI/bot behavior.
    """
    time_s      = metrics.get("time_survived", 0)
    actions     = metrics.get("actions", 0)
    errors      = metrics.get("errors", 0)
    performance = metrics.get("performance", "Low")
    scores      = metrics.get("scores", [0])
    game_type   = metrics.get("game_type", {})

    # ✅ FIXED — Safe division, handle float time_s
    safe_time   = max(float(time_s), 1.0)
    aps         = actions / safe_time

    signals     = []
    human_score = 0
    bot_score   = 0

    # ── Signal 1: Action Rate ──────────────────────────────────
    if 0.3 <= aps <= 2.0:
        human_score += 2
        signals.append(f"Natural action rate ({aps:.2f} APS)")
    elif aps > 3.0:
        bot_score += 2
        signals.append(f"Unusually high action rate ({aps:.2f} APS) - bot-like")
    elif aps == 0:
        bot_score += 1
        signals.append("Zero actions - possible bot that failed to interact")

    # ── Signal 2: Error Pattern ────────────────────────────────
    if 1 <= errors <= 3:
        human_score += 2
        signals.append(f"Natural error count ({errors}) - human-like mistakes")
    elif errors == 0:
        bot_score += 1
        signals.append("Zero errors - suspiciously perfect (possible bot)")
    elif errors > 5:
        bot_score += 1
        signals.append(f"High error count ({errors}) - random/bot behavior")

    # ── Signal 3: Score Progression ───────────────────────────
    if len(scores) > 3:
        diffs = [
            abs(scores[i] - scores[i - 1])
            for i in range(1, len(scores))
        ]
        avg_diff = sum(diffs) / len(diffs)

        # ✅ FIXED — Proper variance check
        variance = (
            sum((d - avg_diff) ** 2 for d in diffs) / len(diffs)
            if len(diffs) > 0 else 0
        )

        # ✅ FIXED — Use relative threshold, not magic number
        threshold = avg_diff * 0.5 if avg_diff > 0 else 1

        if variance > threshold:
            human_score += 2
            signals.append("Variable score progression - human-like pattern")
        else:
            bot_score += 2
            signals.append(
                "Too-consistent score progression - bot-like pattern"
            )

    # ── Signal 4: Timing Pattern ───────────────────────────────
    if 15 <= time_s <= 60:
        human_score += 1
        signals.append(f"Natural session duration ({time_s:.1f}s)")
    elif time_s < 5:
        bot_score += 1
        signals.append("Very short session - possible bot timeout")
    elif time_s > 90:
        human_score += 1
        signals.append(f"Long engagement ({time_s:.1f}s) - human-like")

    # ── Signal 5: Performance Level ────────────────────────────
    if performance == "High":
        bot_score += 1
        signals.append("High performance - possibly AI-assisted")
    elif performance == "Low":
        human_score += 1
        signals.append("Low performance - natural human struggle")
    elif performance == "Medium":
        human_score += 1
        signals.append("Medium performance - typical human range")

    # ── Signal 6: Game Type Behavior ──────────────────────────
    game_type_name = game_type.get("primary_type", "Unknown")
    if game_type_name in ["Card/Board", "Puzzle", "Strategy"]:
        if aps < 1.0:
            human_score += 1
            signals.append(
                f"Thoughtful pace for {game_type_name} - human-like"
            )
    elif game_type_name in ["Endless Runner", "Action/Shooter"]:
        if aps > 1.0:
            human_score += 1
            signals.append(f"Active play for {game_type_name} - normal")

    # ── Determine Final Verdict ────────────────────────────────
    total = human_score + bot_score

    if total == 0:
        return {
            "verdict":    "Uncertain",
            "confidence": "Low",
            "reason":     "Insufficient data to determine player type",
            "signals":    signals
        }

    human_ratio = human_score / total

    if human_ratio >= 0.65:
        verdict    = "Human"
        confidence = "High" if human_ratio >= 0.80 else "Medium"
        reason     = (
            f"Play patterns match human behavior "
            f"({human_score}/{total} signals)"
        )
    elif human_ratio <= 0.35:
        verdict    = "AI/Bot"
        confidence = "High" if human_ratio <= 0.20 else "Medium"
        reason     = (
            f"Play patterns suggest automated testing "
            f"({bot_score}/{total} signals)"
        )
    else:
        verdict    = "Uncertain"
        confidence = "Low"
        reason     = (
            f"Mixed signals - could be either "
            f"(Human: {human_score}, Bot: {bot_score})"
        )

    # ── Enhance with Groq if available ────────────────────────
    client = get_groq_client()
    if client is not None:
        try:
            enhanced = _get_groq_human_verdict(
                url, metrics, signals, verdict, client
            )
            if enhanced:
                return enhanced
        except Exception as e:
            logger.warning(f"Groq verdict enhancement failed: {e}")

    return {
        "verdict":    verdict,
        "confidence": confidence,
        "reason":     reason,
        "signals":    signals[:6]
    }


def _get_groq_human_verdict(
    url: str,
    metrics: dict,
    signals: list,
    initial_verdict: str,
    client: Groq  # ✅ FIXED — Pass client, don't rely on global
) -> dict:
    """
    Use Groq AI to enhance the Human vs AI verdict determination
    """
    time_s      = metrics.get("time_survived", 0)
    actions     = metrics.get("actions", 0)
    errors      = metrics.get("errors", 0)
    performance = metrics.get("performance", "Low")
    scores      = metrics.get("scores", [0])

    # ✅ FIXED — Safe division
    safe_time = max(float(time_s), 1.0)
    aps       = actions / safe_time

    score_progression = "flat"
    if len(scores) > 1:
        if scores[-1] > scores[0] * 1.5:
            score_progression = "growing"
        elif scores[-1] < scores[0]:
            score_progression = "declining"
        else:
            score_progression = "stable"

    prompt = f"""
You are an expert at detecting whether a game session was played by a human or an AI/bot.

GAME SESSION DATA:
- URL: {url}
- Time Played: {time_s} seconds
- Total Actions: {actions}
- Actions Per Second: {aps:.2f}
- Errors Made: {errors}
- Performance: {performance}
- Score Progression: {score_progression}
- Pre-analysis Signals: {', '.join(signals[:5])}
- Initial Verdict: {initial_verdict}

TASK:
Determine if this game session was played by a HUMAN or an AI/BOT.

Respond in EXACTLY this format (no extra text):
VERDICT: [Human/AI Bot/Uncertain]
CONFIDENCE: [High/Medium/Low]
REASON: [One sentence explanation]
KEY SIGNAL: [Most important signal you detected]
"""

    completion = client.chat.completions.create(
        model=model,
        temperature=0.2,
        max_tokens=150,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert game behavior analyst. "
                    "Detect human vs AI/bot gameplay patterns. "
                    "Always respond in the exact format requested. "
                    "Never use markdown."
                )
            },
            {
                "role":    "user",
                "content": prompt
            }
        ]
    )

    response = completion.choices[0].message.content.strip()
    logger.info(f"Groq verdict response: {response}")

    # ✅ FIXED — Safe parsing with validation
    lines  = response.split('\n')
    parsed = {}

    for line in lines:
        if ':' in line:
            key, _, value = line.partition(':')
            parsed[key.strip().upper()] = value.strip()

    # ✅ FIXED — Validate we got something useful
    if not parsed:
        logger.warning("Groq returned unparseable response")
        return None

    verdict    = parsed.get("VERDICT", initial_verdict)
    confidence = parsed.get("CONFIDENCE", "Medium")
    reason     = parsed.get("REASON", "Based on gameplay patterns")
    key_signal = parsed.get("KEY SIGNAL", "")

    # Normalize verdict
    if "bot" in verdict.lower() or "ai" in verdict.lower():
        verdict = "AI/Bot"
    elif "human" in verdict.lower():
        verdict = "Human"
    else:
        verdict = "Uncertain"

    # Normalize confidence
    if confidence.lower() not in ["high", "medium", "low"]:
        confidence = "Medium"

    return {
        "verdict":    verdict,
        "confidence": confidence,
        "reason":     reason,
        "key_signal": key_signal,
        "signals":    signals[:6]
    }


# ── AI Game Conversation ──────────────────────────────────────
def get_ai_game_conversation(
    user_message: str,
    conversation_history: list = None,
    game_context: str = None
) -> str:
    """
    Generate AI reply for game-related chat messages.
    """
    # ✅ FIXED — Fresh client
    client = get_groq_client()

    if client is None:
        return (
            "I'm TestProbe AI, your game testing assistant!\n\n"
            "I can help you with:\n"
            "  Testing game URLs for fairness\n"
            "  Answering questions about web games\n"
            "  Explaining how game testing works\n"
            "  Telling you if a game was played humanly or by AI\n\n"
            "Just paste a game URL to test it, "
            "or ask me anything about games!"
        )

    system_content = (
        "You are TestProbe AI, a friendly and knowledgeable game testing assistant. "
        "You help users test web-based games using Selenium automation. "
        "You can answer questions about:\n"
        "  - What makes a game fair or unfair\n"
        "  - How to identify rigged games\n"
        "  - Web game technologies (HTML5, Canvas, WebGL)\n"
        "  - Game testing methodologies\n"
        "  - Popular game genres and platforms\n"
        "  - Human vs AI gameplay detection\n"
        "  - AI test types and what they measure\n\n"
        "Keep responses helpful, concise, and engaging. "
        "Always encourage users to share game URLs for testing. "
        "Never use markdown formatting. "
        "Use plain text with emojis for friendliness."
    )

    if game_context:
        system_content += (
            f"\n\nIMPORTANT - You have already analyzed a game for this user. "
            f"Use this context to answer their follow-up questions:\n\n"
            f"{game_context}\n"
            f"The user may ask about this game's type, performance, "
            f"whether it was played by human or AI, what tests were run, etc. "
            f"Answer based on the context above."
        )

    try:
        messages = [{"role": "system", "content": system_content}]

        # ✅ FIXED — Validate conversation history
        if conversation_history and isinstance(conversation_history, list):
            recent = conversation_history[-10:]
            for msg in recent:
                # ✅ Safe key access
                if not isinstance(msg, dict):
                    continue
                if "role" not in msg or "content" not in msg:
                    continue
                role = "user" if msg["role"] == "user" else "assistant"
                content = str(msg.get("content", "")).strip()
                if content:  # ✅ Skip empty messages
                    messages.append({
                        "role":    role,
                        "content": content
                    })

        messages.append({
            "role":    "user",
            "content": user_message
        })

        logger.info("Requesting Groq chat reply...")
        completion = client.chat.completions.create(
            model=model,
            temperature=0.7,
            max_tokens=400,
            messages=messages
        )
        reply = completion.choices[0].message.content.strip()
        logger.info("Groq chat reply received")
        return reply

    except Exception as e:
        logger.error(f"Groq chat error: {str(e)[:100]}")
        return (
            "I'm here to help you test games!\n\n"
            "You can:\n"
            "  Send me a game URL to analyze it\n"
            "  Ask about game fairness or testing methods\n"
            "  Ask if a game was played by human or AI\n"
            "  Ask what AI tests were performed\n\n"
            "What would you like to know?"
        )
