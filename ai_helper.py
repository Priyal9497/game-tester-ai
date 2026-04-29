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
    logger.warning("GROQ_API_KEY not found in .env")


# ── AI Test Analysis ──────────────────────────────────────────
def get_ai_test_analysis(url: str, metrics: dict) -> str:
    """
    Generate AI analysis of Selenium test results using Groq
    """
    if client is None:
        return (
            "AI analysis unavailable.\n"
            "Add GROQ_API_KEY to your .env file."
        )

    page_info   = metrics.get("page_info", {})
    time_s      = metrics.get("time_survived", 0)
    actions     = metrics.get("actions", 0)
    errors      = metrics.get("errors", 0)
    performance = metrics.get("performance", "Low")
    has_canvas  = page_info.get("has_canvas", False)
    has_game    = page_info.get("has_game_elements", False)
    page_title  = page_info.get("title", "Unknown")
    load_failed = metrics.get("load_failed", False)

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


# ── AI Chat Reply ─────────────────────────────────────────────
def get_ai_chat_reply(message: str) -> str:
    """
    Generate AI reply for general chat messages using Groq
    """
    if client is None:
        return (
            "I can test game URLs for you!\n"
            "Just paste a URL starting with https://"
        )

    try:
        logger.info("Requesting Groq chat reply...")
        completion = client.chat.completions.create(
            model=model,
            temperature=0.5,
            max_tokens=200,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are TestProbe AI, a browser game testing assistant. "
                        "You help users test web-based games using Selenium automation. "
                        "Keep replies short and friendly. "
                        "Always encourage users to paste a game URL to test. "
                        "Never use markdown formatting."
                    )
                },
                {
                    "role": "user",
                    "content": message
                }
            ]
        )
        reply = completion.choices[0].message.content.strip()
        logger.info("Groq chat reply received")
        return reply

    except Exception as e:
        logger.error(f"Groq chat error: {str(e)[:100]}")
        return (
            "I can help you test web games!\n"
            "Just paste a game URL to get started."
        )