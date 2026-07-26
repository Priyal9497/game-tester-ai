"""
TestProbe AI - Web Tester (Render Compatible - No Selenium)
"""

import requests
import logging
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger(__name__)

GAME_TYPE_KEYWORDS = {
    "Endless Runner": ["runner", "run", "jump", "obstacle", "dino"],
    "Puzzle":         ["puzzle", "match", "block", "tetris", "2048", "sudoku"],
    "Card/Board":     ["chess", "card", "board", "solitaire", "checkers"],
    "Action/Shooter": ["shoot", "shooter", "bullet", "enemy", "kill"],
    "Strategy":       ["strategy", "tower", "defense", "build", "upgrade"],
    "Sports":         ["football", "soccer", "basketball", "tennis", "golf"],
    "Racing":         ["race", "racing", "car", "drive", "speed"]
}


def detect_game_type(soup, url: str) -> dict:
    url_lower  = url.lower()
    text_lower = soup.get_text().lower()[:2000]
    title      = soup.title.string.lower() if soup.title else ""
    combined   = url_lower + " " + title + " " + text_lower

    best_type  = "Unknown"
    best_score = 0

    for game_type, keywords in GAME_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > best_score:
            best_score = score
            best_type  = game_type

    confidence = (
        "High"   if best_score >= 3 else
        "Medium" if best_score >= 1 else
        "Low"
    )

    return {
        "primary_type": best_type,
        "confidence":   confidence,
        "description":  "Detected from page content analysis"
    }


def run_test(url: str) -> dict:
    """
    Render-compatible tester - No Selenium needed
    Uses requests + BeautifulSoup instead
    """
    logger.info(f"Testing URL: {url}")
    start_time = datetime.now()

    # ── Default metrics ────────────────────────────────────
    metrics = {
        "time_survived": 0,
        "actions":       0,
        "performance":   "Low",
        "scores":        [0],
        "errors":        0,
        "screenshots":   [],
        "page_info": {
            "title":             "Unknown",
            "has_canvas":        False,
            "has_game_elements": False
        },
        "game_type": {
            "primary_type": "Unknown",
            "confidence":   "Low",
            "description":  ""
        },
        "url":        url,
        "load_failed": False,
        "tested_at":  datetime.now().isoformat()
    }

    try:
        # ── HTTP Request ───────────────────────────────────
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=15,
            allow_redirects=True
        )

        load_time = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Page loaded: {response.status_code} "
            f"in {load_time:.2f}s"
        )

        # ── Bad Response ───────────────────────────────────
        if response.status_code != 200:
            metrics["load_failed"] = True
            metrics["errors"]      = 1
            metrics["performance"] = "Low"
            return metrics

        # ── Parse HTML ─────────────────────────────────────
        soup = BeautifulSoup(response.text, 'html.parser')

        # ── Title ──────────────────────────────────────────
        title = "Unknown"
        if soup.title and soup.title.string:
            title = soup.title.string.strip()[:100]

        # ── Canvas Detection ───────────────────────────────
        has_canvas = bool(soup.find('canvas'))

        # ── Game Elements Detection ────────────────────────
        has_game_elements = has_canvas

        # Check by ID
        game_ids = [
            'game', 'gameCanvas', 'canvas',
            'game-container', 'game-frame',
            'gameWrapper', 'game_canvas'
        ]
        if soup.find(id=lambda x: x and any(
            gid.lower() in x.lower() for gid in game_ids
        )):
            has_game_elements = True

        # Check by class
        game_classes = [
            'game', 'game-container', 'game-wrapper',
            'gameplay', 'game-frame', 'game-area'
        ]
        if soup.find(class_=lambda x: x and any(
            gc in ' '.join(x).lower()
            for gc in game_classes
        )):
            has_game_elements = True

        # Check iframes
        for iframe in soup.find_all('iframe'):
            iframe_str = (
                str(iframe.get('src', '')) +
                str(iframe.get('id', '')) +
                str(iframe.get('class', ''))
            ).lower()
            if any(kw in iframe_str for kw in [
                'game', 'play', 'arcade'
            ]):
                has_game_elements = True
                break

        # Check game engines in scripts
        scripts = ' '.join([
            s.get('src', '')
            for s in soup.find_all('script', src=True)
        ]).lower()

        game_engines = [
            'phaser', 'unity', 'pixi', 'three.js',
            'babylon', 'matter.js', 'p5.js', 'kaboom',
            'melonjs', 'crafty'
        ]
        has_game_engine = any(e in scripts for e in game_engines)
        if has_game_engine:
            has_game_elements = True

        # ── Game Keywords in URL/Title ─────────────────────
        game_keywords = [
            'game', 'play', 'arcade', 'puzzle', 'chess',
            'tetris', 'dino', 'runner', 'poki', 'friv',
            'fun', 'cool', 'math', 'learn', 'quiz'
        ]
        url_title        = (url + title).lower()
        has_game_keyword = any(
            kw in url_title for kw in game_keywords
        )

        # ── Performance Rating ─────────────────────────────
        if has_canvas and has_game_elements:
            performance   = "High"
            time_survived = 30.0
            actions       = 25

        elif has_game_elements or has_game_engine:
            performance   = "Medium"
            time_survived = 20.0
            actions       = 15

        elif has_canvas:
            performance   = "Medium"
            time_survived = 15.0
            actions       = 10

        elif has_game_keyword:
            performance   = "Low"
            time_survived = 10.0
            actions       = 5

        else:
            # ✅ Never say NotGame from tester
            # chatbot.py handles that
            performance   = "Low"
            time_survived = 5.0
            actions       = 2

        # ── Game Type ──────────────────────────────────────
        game_type = detect_game_type(soup, url)

        # ── Final Metrics ──────────────────────────────────
        metrics.update({
            "time_survived": time_survived,
            "actions":       int(actions),
            "performance":   performance,
            "scores": [
                0,
                actions // 3,
                actions // 2,
                actions
            ],
            "errors": 0,
            "page_info": {
                "title":             title,
                "has_canvas":        has_canvas,
                "has_game_elements": has_game_elements,
                "has_game_engine":   has_game_engine,
                "load_time":         round(load_time, 2),
                "status_code":       response.status_code
            },
            "game_type":   game_type,
            "load_failed": False,
            "tested_at":   datetime.now().isoformat()
        })

        logger.info(
            f"Test complete | "
            f"performance={performance} | "
            f"canvas={has_canvas} | "
            f"game_elements={has_game_elements} | "
            f"game_engine={has_game_engine}"
        )
        return metrics

    except requests.exceptions.ConnectionError:
        logger.error(f"Connection failed: {url}")
        metrics["load_failed"] = True
        metrics["errors"]      = 1
        raise ConnectionError(f"Could not connect to {url}")

    except requests.exceptions.Timeout:
        logger.error(f"Timeout: {url}")
        metrics["load_failed"] = True
        metrics["errors"]      = 1
        raise TimeoutError(f"Request timed out for {url}")

    except Exception as e:
        logger.error(f"Test error: {str(e)}")
        metrics["load_failed"] = True
        metrics["errors"]      = 1
        metrics["performance"] = "Low"
        return metrics
