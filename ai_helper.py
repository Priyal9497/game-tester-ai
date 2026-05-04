"""
TestProbe AI - Groq AI Analysis Helper
"""

import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

# ── Initialize Groq Client ────────────────────────────────────
api_key = os.getenv("GROQ_API_KEY")
model   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
client  = None

if api_key:
    try:
        client = Groq(api_key=api_key)
        logger.info("Groq client initialized successfully")
    except Exception as e:
        logger.error(f"Groq init failed: {e}")
else:
    logger.warning("GROQ_API_KEY not found in environment")


# ── AI Test Analysis ──────────────────────────────────────────
def get_ai_test_analysis(url: str, metrics: dict) -> str:
    """
    Generate AI analysis of Selenium test results using Groq
    """
    if client is None:
        return "AI analysis unavailable. Add GROQ_API_KEY to your environment variables."

    page_info   = metrics.get("page_info", {})
    time_s      = metrics.get("time_survived", 0)
    actions     = metrics.get("actions", 0)
    errors      = metrics.get("errors", 0)
    performance = metrics.get("performance", "Low")
    has_canvas  = page_info.get("has_canvas", False)
    has_game    = page_info.get("has_game_elements", False)
    page_title  = page_info.get("title", "Unknown")
    load_failed = metrics.get("load_failed", False)

    # Short-circuit for failed loads
    if load_failed:
        return (
            "VERDICT: No\n"
            "ASSESSMENT: The page failed to load or render game elements.\n"
            "ISSUES: Selenium could not access or detect playable content.\n"
            "SUGGESTION: Check for anti-bot protection, iframe embedding, or JS-heavy lazy loading.\n"
            "NEXT STEP: Test manually in a regular browser, then retry with updated wait strategies."
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

Based on these results provide:

1. VERDICT: Is this a valid playable game? (Yes/No/Uncertain)
2. ASSESSMENT: One sentence overall assessment
3. ISSUES: Main problem found if any
4. SUGGESTION: One specific improvement suggestion
5. NEXT STEP: What should tester do next

Keep each point to 1-2 sentences maximum.
Be direct and practical.
Do not use markdown or special formatting.
"""

    try:
        logger.info("Requesting Groq AI analysis...")
        completion = client.chat.completions.create(
            model=model,
            temperature=0.3,
            max_tokens=300,
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
                    "role": "user",
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


# ── AI Game Conversation ──────────────────────────────────────
def get_ai_game_conversation(user_message: str, conversation_history: list = None) -> str:
    """
    Generate AI reply for game-related chat messages with conversation context
    """
    if client is None:
        return (
            "I'm TestProbe AI, your game testing assistant!\n\n"
            "I can help you with:\n"
            "  Testing game URLs for fairness\n"
            "  Answering questions about web games\n"
            "  Explaining how game testing works\n\n"
            "Just paste a game URL to test it, or ask me anything about games!"
        )

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are TestProbe AI, a friendly and knowledgeable game testing assistant. "
                    "You help users test web-based games using Selenium automation. "
                    "You can answer questions about:\n"
                    "  - What makes a game fair or unfair\n"
                    "  - How to identify rigged games\n"
                    "  - Web game technologies (HTML5, Canvas, WebGL)\n"
                    "  - Game testing methodologies\n"
                    "  - Popular game genres and platforms\n\n"
                    "Keep your responses helpful, concise, and engaging. "
                    "Always encourage users to share game URLs for testing. "
                    "If asked about non-game topics, politely redirect to game-related discussions. "
                    "Never use markdown formatting. Use plain text with emojis for friendliness."
                )
            }
        ]

        # Add conversation history (last 10 messages for context)
        if conversation_history and len(conversation_history) > 0:
            recent = conversation_history[-10:]
            for msg in recent:
                role = "user" if msg["role"] == "user" else "assistant"
                messages.append({
                    "role": role,
                    "content": msg["content"]
                })

        # Add current message
        messages.append({
            "role": "user",
            "content": user_message
        })

        logger.info("Requesting Groq chat reply with context...")
        completion = client.chat.completions.create(
            model=model,
            temperature=0.7,
            max_tokens=300,
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
            "  Send me a game URL (like https://chromedino.com) to test it\n"
            "  Ask me about game fairness or testing methods\n"
            "  Get tips on finding good web games\n\n"
            "What would you like to know about games?"
        )