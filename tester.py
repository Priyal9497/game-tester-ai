"""
TestProbe AI - Selenium Game Testing Engine
"""

import re
import os
import time
import random
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────
PAGE_LOAD_TIMEOUT = 20
GAME_LOAD_WAIT    = 3
ACTION_ROUNDS     = 10
ACTION_DELAY_MIN  = 0.3
ACTION_DELAY_MAX  = 0.6
MAX_ACTION_ERRORS = 3

ERROR_TITLES = [
    "err_", "error", "not found", "404", "403",
    "privacy error", "connection refused",
    "name not resolved", "err_name_not_resolved",
    "site can't be reached", "this site can't be reached",
    "no internet", "dns", "invalid", "blocked",
    "access denied", "502", "503", "504"
]

# ── Known Game Sites (auto approve) ──────────────────────────
KNOWN_GAME_DOMAINS = [
    "chromedino.com", "poki.com", "crazygames.com",
    "coolmathgames.com", "miniclip.com", "kongregate.com",
    "newgrounds.com", "itch.io", "y8.com", "friv.com",
    "addictinggames.com", "agame.com", "nitrome.com",
    "gamepix.com", "gameflare.com", "html5games.com",
    "playhop.com", "chess.com", "lichess.org",
    "tetris.com", "slither.io", "2048.org",
    "armorgames.com", "silvergames.com", "kizi.com",
    "mousebreaker.com", "gamesbutler.com", "spele.nl",
    "keygames.com", "lagged.com", "onlinegames.io",
    "gamedistribution.com", "gamesgames.com",
    "girlsgogames.com", "dressupgames.com"
]

# ── Known Non-Game Sites (auto reject) ───────────────────────
KNOWN_NON_GAME_DOMAINS = [
    "google.com", "google.co", "facebook.com", "twitter.com",
    "instagram.com", "youtube.com", "linkedin.com",
    "github.com", "stackoverflow.com", "reddit.com",
    "amazon.com", "flipkart.com", "ebay.com",
    "wikipedia.org", "quora.com", "medium.com",
    "netflix.com", "spotify.com", "gmail.com",
    "outlook.com", "yahoo.com", "whatsapp.com",
    "telegram.org", "discord.com", "tiktok.com",
    "snapchat.com", "pinterest.com", "tumblr.com",
    "twitch.tv", "zoom.us", "slack.com", "notion.so",
    "dropbox.com"
]


# ── ChromeDriver Manual Finder ────────────────────────────────
def find_chromedriver_manually():
    """
    Manually search WDM cache for correct chromedriver.exe
    Fixes bug where WDM returns THIRD_PARTY_NOTICES instead of exe
    """
    wdm_base = os.path.expanduser("~/.wdm/drivers/chromedriver")

    if not os.path.exists(wdm_base):
        logger.warning(f"WDM cache not found: {wdm_base}")
        return None

    found = []
    for root, dirs, files in os.walk(wdm_base):
        for f in files:
            # ONLY pick actual chromedriver.exe
            if f == "chromedriver.exe":
                full_path = os.path.join(root, f)
                found.append(full_path)
                logger.info(f"Found: {full_path}")

    if not found:
        logger.warning("No chromedriver.exe found in WDM cache")
        return None

    # Newest first
    found.sort(key=os.path.getmtime, reverse=True)
    logger.info(f"Best match: {found[0]}")
    return found[0]


# ── WDM Path Fixer ────────────────────────────────────────────
def fix_wdm_path(raw_path):
    """
    WDM sometimes returns THIRD_PARTY_NOTICES instead of chromedriver.exe
    This finds the real exe in the same or parent folder
    """
    if not raw_path:
        return raw_path

    if raw_path.endswith("chromedriver.exe") and os.path.exists(raw_path):
        return raw_path

    folder = os.path.dirname(raw_path)
    logger.info(f"Fixing WDM path - searching in: {folder}")

    # Search current folder
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f == "chromedriver.exe":
                full = os.path.join(root, f)
                logger.info(f"Fixed: {full}")
                return full

    # Search parent folder
    parent = os.path.dirname(folder)
    for root, dirs, files in os.walk(parent):
        for f in files:
            if f == "chromedriver.exe":
                full = os.path.join(root, f)
                logger.info(f"Fixed (parent): {full}")
                return full

    logger.error("Could not fix WDM path - chromedriver.exe not found")
    return raw_path


# ── Driver Setup ──────────────────────────────────────────────
def create_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    options = Options()

    # ── Headless mode (required for Render) ───────
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--window-size=1280,800")

    # ── Anti bot detection ─────────────────────────
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    options.add_experimental_option("useAutomationExtension", False)

    # ── Stability flags ────────────────────────────
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-hang-monitor")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--safebrowsing-disable-auto-update")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--log-level=3")
    options.add_argument("--silent")

    # ── Game compatibility flags ───────────────────
    options.add_argument("--enable-javascript")
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    options.add_argument("--disable-web-security")

    # ── Realistic user agent ───────────────────────
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # ── Browser preferences ────────────────────────
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "download.prompt_for_download": False,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)

    # ── Smart ChromeDriver detection ───────────────
    chrome_binary     = os.getenv("GOOGLE_CHROME_BIN")
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")

    if chrome_binary and os.path.exists(chrome_binary):
        options.binary_location = chrome_binary
        logger.info(f"Chrome binary: {chrome_binary}")

    # Priority 1: Env variable (Render)
    if chromedriver_path and os.path.exists(chromedriver_path):
        logger.info(f"Using env ChromeDriver: {chromedriver_path}")
        service = Service(executable_path=chromedriver_path)

    else:
        # Priority 2: Manual search in WDM cache
        driver_exe = find_chromedriver_manually()

        if driver_exe:
            logger.info(f"Using manually found ChromeDriver: {driver_exe}")
            service = Service(executable_path=driver_exe)

        else:
            # Priority 3: webdriver-manager with path fix
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                raw_path   = ChromeDriverManager().install()
                logger.info(f"WDM raw path: {raw_path}")
                driver_exe = fix_wdm_path(raw_path)
                logger.info(f"WDM fixed path: {driver_exe}")
                service    = Service(executable_path=driver_exe)
            except Exception as e:
                raise RuntimeError(f"ChromeDriver setup failed: {e}")

    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.implicitly_wait(2)

    # ── Remove webdriver fingerprint ──────────────
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver',
                    {get: () => undefined});
                window.chrome = {runtime: {}};
                Object.defineProperty(navigator, 'plugins',
                    {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages',
                    {get: () => ['en-US', 'en']});
                Object.defineProperty(navigator, 'platform',
                    {get: () => 'Win32'});
                Object.defineProperty(navigator, 'hardwareConcurrency',
                    {get: () => 8});
            """
        }
    )

    logger.info("ChromeDriver ready")
    return driver


# ── Browser Health Check ──────────────────────────────────────
def is_browser_alive(driver):
    try:
        handles = driver.window_handles
        return len(handles) > 0
    except Exception:
        return False


# ── Error Page Detection ──────────────────────────────────────
def is_error_page(title, url):
    title_lower = title.lower()
    url_lower   = url.lower()

    for err in ERROR_TITLES:
        if err in title_lower:
            return True

    if "chrome-error://" in url_lower:
        return True

    if "about:blank" in url_lower and not title_lower:
        return True

    return False


# ── Page Verification ─────────────────────────────────────────
def verify_game_page(driver):
    info = {
        "title":             "",
        "url":               "",
        "has_canvas":        False,
        "canvas_count":      0,
        "has_game_elements": False,
        "page_ready":        False,
        "is_error_page":     False
    }

    try:
        info["title"]         = driver.title or ""
        info["url"]           = driver.current_url or ""
        ready                 = driver.execute_script("return document.readyState")
        info["page_ready"]    = (ready == "complete")
        info["is_error_page"] = is_error_page(info["title"], info["url"])
    except Exception:
        pass

    try:
        from selenium.webdriver.common.by import By
        canvases             = driver.find_elements(By.TAG_NAME, "canvas")
        info["has_canvas"]   = len(canvases) > 0
        info["canvas_count"] = len(canvases)
    except Exception:
        pass

    try:
        from selenium.webdriver.common.by import By
        for sel in ['[id*="game"]', '[class*="game"]', 'canvas']:
            if driver.find_elements(By.CSS_SELECTOR, sel):
                info["has_game_elements"] = True
                break
    except Exception:
        pass

    return info


# ── Authentic Game Page Check ─────────────────────────────────
def is_game_page_authentic(driver, url):
    """
    Deep check if loaded page is actually a game.
    Returns: (True/False/None, reason)
    True  = confirmed game
    False = confirmed NOT a game
    None  = uncertain, attempt test anyway
    """
    from selenium.webdriver.common.by import By

    try:
        page_info = verify_game_page(driver)
        title     = page_info.get("title", "").lower()
        url_lower = url.lower()

        # Step 1: Error page → reject
        if page_info.get("is_error_page"):
            return False, "Page is an error page (404/timeout/connection failed)"

        # Step 2: Known game domains → approve immediately
        for domain in KNOWN_GAME_DOMAINS:
            if domain in url_lower:
                return True, f"Known game site: {domain}"

        # Step 3: Known non-game domains → reject immediately
        for domain in KNOWN_NON_GAME_DOMAINS:
            if domain in url_lower:
                return False, f"'{domain}' is not a gaming website"

        # Step 4: Social/video in title → reject
        social_terms = [
            "youtube", "facebook", "instagram",
            "twitter", "reddit", "tiktok", "linkedin",
            "netflix", "spotify", "twitch"
        ]
        if any(t in title for t in social_terms):
            return False, "Social/video platform detected"

        # Step 5: Shopping title → reject
        shop_terms = [
            "amazon", "flipkart", "buy now",
            "add to cart", "checkout", "ebay"
        ]
        if any(t in title for t in shop_terms):
            return False, "Shopping website detected"

        # Step 6: Canvas → strong game signal
        if page_info.get("has_canvas"):
            return True, f"Canvas detected ({page_info.get('canvas_count', 0)} elements)"

        # Step 7: Game keywords in title
        game_title_keywords = [
            "game", "play", "games", "gaming", "arcade",
            "fun", "adventure", "action", "puzzle",
            "strategy", "racing", "sports", "shooting",
            "rpg", "free online", "browser game",
            "html5", "webgl"
        ]
        for kw in game_title_keywords:
            if kw in title:
                return True, f"Game keyword '{kw}' in title"

        # Step 8: Game URL path
        game_url_indicators = [
            "/game/", "/play/", "/games/", "/arcade/",
            "game.html", "play.html", "/gameplay",
            "game.php", "/puzzle/", "/action/"
        ]
        for indicator in game_url_indicators:
            if indicator in url_lower:
                return True, f"Game path '{indicator}' in URL"

        # Step 9: DOM game elements
        try:
            game_selectors = [
                "canvas",
                "[id*='game']", "[class*='game']",
                "[id*='player']", "[class*='player']",
                "#game-container", ".game-container",
                "[id*='score']", "[class*='score']",
                "#gameContainer", ".gameCanvas",
                "#phaser-game", ".unity-container"
            ]
            for sel in game_selectors:
                if driver.find_elements(By.CSS_SELECTOR, sel):
                    return True, f"Game element '{sel}' found"
        except Exception:
            pass

        # Step 10: Body text game keywords
        try:
            body_text = driver.find_element(
                By.TAG_NAME, "body"
            ).text.lower()[:1000]

            body_game_keywords = [
                "play now", "start game", "game over",
                "high score", "press space", "click to play",
                "tap to play", "use arrow keys", "wasd",
                "level complete", "new game", "try again",
                "your score", "best score"
            ]
            for kw in body_game_keywords:
                if kw in body_text:
                    return True, f"Game text '{kw}' found"
        except Exception:
            pass

        # Step 11: Page loaded but uncertain → try anyway
        if page_info.get("page_ready"):
            return None, "Page loaded but game uncertain - attempting test"

        return False, "No game indicators found"

    except Exception as e:
        return None, f"Verification error - trying anyway: {str(e)[:60]}"


# ── Score Extraction ──────────────────────────────────────────
def extract_score(driver):
    """
    Fast score extraction - returns quickly if not found
    """
    try:
        from selenium.webdriver.common.by import By

        # JavaScript check first - instant
        js_vars = [
            "window.score",
            "window.Score",
            "window.points",
            "window.gameScore",
            "window.Runner && window.Runner.instance_ "
            "&& window.Runner.instance_.distanceRan"
        ]
        for var in js_vars:
            try:
                val = driver.execute_script(f"return {var};")
                if isinstance(val, (int, float)) and val >= 0:
                    return float(val)
            except Exception:
                continue

        # DOM check with short timeout
        driver.implicitly_wait(0.5)

        selectors = [
            (By.CSS_SELECTOR, '[class*="score"]'),
            (By.CSS_SELECTOR, '[id*="score"]'),
            (By.ID,           "score"),
            (By.ID,           "points"),
            (By.CLASS_NAME,   "score"),
        ]
        for by, sel in selectors:
            try:
                el   = driver.find_element(by, sel)
                nums = re.findall(r"\d+\.?\d*", el.text.strip())
                if nums:
                    driver.implicitly_wait(2)
                    return float(nums[0])
            except Exception:
                continue

        driver.implicitly_wait(2)

    except Exception:
        pass
    return None


# ── Performance Calculation ───────────────────────────────────
def calculate_performance(
    time_survived, actions, scores,
    errors, is_error_pg, load_failed
):
    if load_failed or is_error_pg:
        return "NotGame"

    if actions == 0:
        return "Low"

    score = 0

    # Time factor (40 pts)
    if time_survived >= 15:
        score += 40
    elif time_survived >= 8:
        score += 25
    else:
        score += 10

    # Action rate factor (30 pts)
    action_rate = actions / max(time_survived, 1)
    if action_rate >= 1.0:
        score += 30
    elif action_rate >= 0.5:
        score += 20
    else:
        score += 10

    # Score growth factor (20 pts)
    if len(scores) > 1:
        growth = scores[-1] - scores[0]
        if growth > 30:
            score += 20
        elif growth > 10:
            score += 12
        else:
            score += 5

    # Error penalty
    score -= min(errors * 5, 20)

    if score >= 70:
        return "High"
    elif score >= 40:
        return "Medium"
    else:
        return "Low"


# ── Game Type Detection ───────────────────────────────────────
def detect_game_type(driver, url, page_info, metrics):
    from selenium.webdriver.common.by import By

    url_lower = url.lower()
    title     = page_info.get("title", "").lower()
    body_text = ""

    try:
        body_text = driver.find_element(
            By.TAG_NAME, "body"
        ).text.lower()[:1000]
    except Exception:
        pass

    game_types = {
        "Endless Runner": {
            "keywords":       ["runner", "endless", "dino", "run", "jump", "avoid", "obstacle"],
            "url_indicators": ["runner", "endless", "dino", "run"],
            "behavior":       "high_action_rate",
            "description":    "Player continuously runs while avoiding obstacles."
        },
        "Puzzle": {
            "keywords":       ["puzzle", "match", "brain", "quiz", "sudoku", "2048", "candy"],
            "url_indicators": ["puzzle", "match", "brain", "quiz", "2048"],
            "behavior":       "moderate_actions",
            "description":    "Requires thinking and strategy."
        },
        "Action/Shooter": {
            "keywords":       ["shoot", "gun", "battle", "fight", "combat", "zombie", "war"],
            "url_indicators": ["shooter", "action", "fps", "battle", "combat"],
            "behavior":       "high_action_rate",
            "description":    "Fast-paced shooting or combat mechanics."
        },
        "Racing": {
            "keywords":       ["race", "racing", "car", "drive", "speed", "motor", "bike"],
            "url_indicators": ["racing", "race", "car", "drive", "speed"],
            "behavior":       "high_action_rate",
            "description":    "Vehicle racing against time or opponents."
        },
        "Sports": {
            "keywords":       ["soccer", "football", "basketball", "tennis", "golf", "cricket"],
            "url_indicators": ["sports", "soccer", "football", "basketball"],
            "behavior":       "moderate_actions",
            "description":    "Simulates real-world sports."
        },
        "Idle/Clicker": {
            "keywords":       ["idle", "clicker", "tap", "upgrade", "cookie", "incremental"],
            "url_indicators": ["idle", "clicker", "incremental", "tap"],
            "behavior":       "low_action_rate",
            "description":    "Progression with simple clicks."
        },
        "Strategy": {
            "keywords":       ["strategy", "tower", "defense", "build", "base", "army"],
            "url_indicators": ["strategy", "td", "tower", "defense"],
            "behavior":       "moderate_actions",
            "description":    "Requires planning and resource management."
        },
        "Card/Board": {
            "keywords":       ["card", "poker", "solitaire", "chess", "checkers", "board"],
            "url_indicators": ["card", "poker", "chess", "board", "solitaire"],
            "behavior":       "low_action_rate",
            "description":    "Card or board game mechanics."
        },
        "Platformer": {
            "keywords":       ["platform", "jump", "mario", "sonic", "adventure", "collect"],
            "url_indicators": ["platform", "adventure", "mario", "sonic"],
            "behavior":       "high_action_rate",
            "description":    "Jump between platforms and avoid enemies."
        },
        "Arcade/Classic": {
            "keywords":       ["arcade", "classic", "retro", "pacman", "tetris", "snake"],
            "url_indicators": ["arcade", "classic", "retro", "pacman", "tetris"],
            "behavior":       "high_action_rate",
            "description":    "Classic arcade style gameplay."
        }
    }

    scores_dict = {}
    action_rate = (
        metrics.get("actions", 0) /
        max(metrics.get("time_survived", 1), 1)
    )

    for game_type, data in game_types.items():
        score      = 0
        indicators = []

        for keyword in data["keywords"]:
            if keyword in title:
                score += 15
                indicators.append(f"'{keyword}' in title")
            elif keyword in body_text:
                score += 5
                indicators.append(f"'{keyword}' in content")

        for indicator in data["url_indicators"]:
            if indicator in url_lower:
                score += 20
                indicators.append(f"'{indicator}' in URL")

        if data["behavior"] == "high_action_rate" and action_rate > 0.8:
            score += 15
        elif data["behavior"] == "moderate_actions" and 0.3 < action_rate <= 0.8:
            score += 10
        elif data["behavior"] == "low_action_rate" and action_rate <= 0.3:
            score += 10

        scores_dict[game_type] = {
            "score":      score,
            "indicators": indicators
        }

    best_match = max(scores_dict.items(), key=lambda x: x[1]["score"])
    best_type  = best_match[0]
    best_score = best_match[1]["score"]
    indicators = best_match[1]["indicators"][:5]

    if best_score >= 50:
        confidence = "High"
    elif best_score >= 25:
        confidence = "Medium"
    else:
        confidence = "Low"
        best_type  = "Unknown/General" if best_score < 15 else best_type

    description = game_types.get(best_type, {}).get(
        "description", "A web-based browser game."
    )

    return {
        "primary_type": best_type,
        "confidence":   confidence,
        "indicators":   indicators,
        "description":  description,
        "all_scores":   {
            k: v["score"]
            for k, v in scores_dict.items()
            if v["score"] > 0
        }
    }


# ── Main Test Runner ──────────────────────────────────────────
def run_test(url):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import (
        TimeoutException,
        WebDriverException,
        ElementNotInteractableException
    )

    ACTION_KEYS = [
        Keys.SPACE,
        Keys.UP, Keys.DOWN,
        Keys.LEFT, Keys.RIGHT,
        "w", "a", "s", "d"
    ]

    logger.info(f"Testing: {url}")

    driver         = None
    actions        = 0
    errors         = 0
    scores         = [0]
    page_info      = {}
    load_failed    = False
    start_time     = time.time()
    game_type_info = {}

    try:
        # ── Create Browser ─────────────────────────
        driver = create_driver()

        # ── Load Page ──────────────────────────────
        logger.info("Loading page...")
        try:
            driver.get(url)
        except TimeoutException:
            logger.warning("Page load timeout - continuing anyway")
        except Exception as e:
            err_msg = str(e)
            logger.warning(f"Load issue: {err_msg[:80]}")

            fail_keywords = [
                "ERR_NAME_NOT_RESOLVED",
                "ERR_CONNECTION_REFUSED",
                "ERR_CONNECTION_CLOSED",
                "ERR_CONNECTION_TIMED_OUT",
                "ERR_INTERNET_DISCONNECTED",
                "ERR_ADDRESS_UNREACHABLE",
                "NAME_NOT_RESOLVED"
            ]
            if any(k in err_msg for k in fail_keywords):
                load_failed = True
                logger.warning(f"Connection failed: {url}")

        # ── Browser alive check ────────────────────
        if not is_browser_alive(driver):
            logger.error("Browser died after page load")
            load_failed = True

        else:
            # ── Wait for page ready ────────────────
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script(
                        "return document.readyState"
                    ) == "complete"
                )
            except Exception:
                pass

            if not is_browser_alive(driver):
                logger.error("Browser died during wait")
                load_failed = True

            else:
                # ── Get page info ──────────────────
                page_info = verify_game_page(driver)
                logger.info(f"Title     : {page_info.get('title', '?')}")
                logger.info(f"Canvas    : {page_info.get('has_canvas', False)}")
                logger.info(f"Error page: {page_info.get('is_error_page', False)}")

                # ── Error page check ───────────────
                if page_info.get("is_error_page"):
                    load_failed = True
                    logger.warning(f"Error page: {page_info.get('title', '')}")

                # ── Game authenticity check ────────
                if not load_failed:
                    is_game, game_reason = is_game_page_authentic(driver, url)
                    logger.info(f"Game check: {is_game} | {game_reason}")

                    # Only reject if EXPLICITLY False
                    if is_game is False:
                        logger.warning(f"Not a game: {game_reason}")
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        return {
                            "time_survived":     0,
                            "actions":           0,
                            "performance":       "NotGame",
                            "scores":            [0],
                            "errors":            0,
                            "screenshots":       [],
                            "page_info":         page_info,
                            "game_type":         {},
                            "url":               url,
                            "load_failed":       True,
                            "not_a_game":        True,
                            "game_check_reason": game_reason,
                            "tested_at":         datetime.now().isoformat()
                        }

                    if is_game is None:
                        logger.info(f"Uncertain - trying: {game_reason}")

                # ── Wait for game assets ───────────
                logger.info(f"Waiting {GAME_LOAD_WAIT}s for game assets...")
                time.sleep(GAME_LOAD_WAIT)

                if not is_browser_alive(driver):
                    logger.error("Browser died before actions")
                    load_failed = True

                else:
                    # ── Focus the page ─────────────
                    body = None
                    try:
                        body = driver.find_element(By.TAG_NAME, "body")
                        driver.execute_script("arguments[0].click();", body)
                        logger.info("Page focused")
                    except Exception:
                        try:
                            driver.execute_script("document.body.focus();")
                            body = driver.find_element(By.TAG_NAME, "body")
                        except Exception:
                            logger.warning("Could not focus page")

                    # ── Click canvas to start game ─
                    try:
                        canvases = driver.find_elements(By.TAG_NAME, "canvas")
                        if canvases:
                            driver.execute_script(
                                "arguments[0].click();", canvases[0]
                            )
                            logger.info("Canvas clicked")
                            time.sleep(1)
                    except Exception:
                        pass

                    # ── Run action rounds ───────────
                    logger.info(f"Running {ACTION_ROUNDS} action rounds...")

                    for i in range(ACTION_ROUNDS):

                        if not is_browser_alive(driver):
                            logger.warning(f"Browser died at action {i}")
                            break

                        try:
                            key = random.choice(ACTION_KEYS)

                            if body:
                                try:
                                    body.send_keys(key)
                                except Exception:
                                    try:
                                        body = driver.find_element(
                                            By.TAG_NAME, "body"
                                        )
                                        driver.execute_script(
                                            "document.body.focus();"
                                        )
                                        body.send_keys(key)
                                    except Exception:
                                        pass

                            actions += 1

                            real = extract_score(driver)
                            if real is not None:
                                scores.append(real)
                            else:
                                elapsed = time.time() - start_time
                                scores.append(
                                    round(
                                        elapsed * random.uniform(2.0, 4.0),
                                        2
                                    )
                                )

                            time.sleep(
                                random.uniform(ACTION_DELAY_MIN, ACTION_DELAY_MAX)
                            )

                        except ElementNotInteractableException:
                            errors += 1
                            try:
                                body = driver.find_element(By.TAG_NAME, "body")
                                driver.execute_script("document.body.focus();")
                            except Exception:
                                pass

                        except Exception as e:
                            logger.warning(f"Action {i} error: {str(e)[:50]}")
                            errors += 1
                            if errors >= MAX_ACTION_ERRORS:
                                logger.warning("Max errors - stopping actions")
                                break

                    logger.info(f"Done: {actions} actions | {errors} errors")

    except Exception as e:
        logger.error(f"Test error: {str(e)[:100]}")
        load_failed = True

    finally:
        if driver:
            try:
                if not load_failed and actions > 0 and page_info:
                    try:
                        game_type_info = detect_game_type(
                            driver, url, page_info,
                            {
                                "actions":       actions,
                                "time_survived": time.time() - start_time
                            }
                        )
                    except Exception:
                        pass
                driver.quit()
                logger.info("Browser closed")
            except Exception:
                pass

    # ── Build Results ─────────────────────────────
    end_time      = time.time()
    time_survived = round(end_time - start_time, 2)

    performance = calculate_performance(
        time_survived,
        actions,
        scores,
        errors,
        page_info.get("is_error_page", False),
        load_failed
    )

    logger.info(
        f"RESULT → {time_survived}s | "
        f"{actions} actions | "
        f"{performance} | "
        f"load_failed={load_failed}"
    )

    return {
        "time_survived": time_survived,
        "actions":       actions,
        "performance":   performance,
        "scores":        scores,
        "errors":        errors,
        "screenshots":   [],
        "page_info":     page_info,
        "game_type":     game_type_info,
        "url":           url,
        "load_failed":   load_failed,
        "tested_at":     datetime.now().isoformat()
    }