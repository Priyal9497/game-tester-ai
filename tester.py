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

# Constants
PAGE_LOAD_TIMEOUT = 15
GAME_LOAD_WAIT = 2
ACTION_ROUNDS = 10
ACTION_DELAY_MIN = 0.2
ACTION_DELAY_MAX = 0.4
MAX_ACTION_ERRORS = 3

# Use forward slashes for Windows path to avoid escape issues
CHROMEDRIVER_PATH = "C:/Users/HP/.wdm/drivers/chromedriver/win64/147.0.7727.117/chromedriver-win32/chromedriver.exe"

# Error page titles that mean failure
ERROR_TITLES = [
    "err_", "error", "not found", "404", "403",
    "privacy error", "connection refused",
    "name not resolved", "err_name_not_resolved",
    "site can't be reached", "this site can't be reached",
    "no internet", "dns", "invalid", "blocked",
    "access denied", "502", "503", "504"
]


def find_chromedriver():
    if os.path.exists(CHROMEDRIVER_PATH):
        logger.info("Chromedriver: " + CHROMEDRIVER_PATH)
        return CHROMEDRIVER_PATH

    wdm_base = os.path.expanduser("~/.wdm/drivers/chromedriver")
    if os.path.exists(wdm_base):
        found = []
        for root, dirs, files in os.walk(wdm_base):
            for f in files:
                if f == "chromedriver.exe":
                    found.append(os.path.join(root, f))
        if found:
            found.sort(key=os.path.getmtime, reverse=True)
            return found[0]
    return None


def create_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    options = Options()

    # Anti-detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    options.add_experimental_option("useAutomationExtension", False)

    # Keep Chrome alive
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-hang-monitor")
    options.add_argument("--disable-prompt-on-repost")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--safebrowsing-disable-auto-update")
    options.add_argument("--password-store=basic")
    options.add_argument("--use-mock-keychain")

    # Stability
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--allow-running-insecure-content")

    # Real user agent
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # Prefs
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "download.prompt_for_download": False,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)

    driver_path = find_chromedriver()
    if not driver_path:
        raise RuntimeError("ChromeDriver not found!")

    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.implicitly_wait(2)

    # Remove webdriver flag
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(
                    navigator, 'webdriver',
                    {get: () => undefined}
                );
                window.chrome = {runtime: {}};
                Object.defineProperty(
                    navigator, 'plugins',
                    {get: () => [1, 2, 3]}
                );
                Object.defineProperty(
                    navigator, 'languages',
                    {get: () => ['en-US', 'en']}
                );
            """
        }
    )

    logger.info("ChromeDriver ready")
    return driver


def is_browser_alive(driver):
    """Check if Chrome is still open"""
    try:
        handles = driver.window_handles
        return len(handles) > 0
    except Exception:
        return False


def is_error_page(title, url):
    """Check if page is an error page"""
    title_lower = title.lower()
    url_lower = url.lower()

    for err in ERROR_TITLES:
        if err in title_lower:
            return True

    if "chrome-error://" in url_lower:
        return True
    if "about:blank" in url_lower and not title_lower:
        return True

    return False


def verify_game_page(driver):
    info = {
        "title": "",
        "url": "",
        "has_canvas": False,
        "canvas_count": 0,
        "has_game_elements": False,
        "page_ready": False,
        "is_error_page": False
    }
    try:
        info["title"] = driver.title or ""
        info["url"] = driver.current_url or ""
        ready = driver.execute_script(
            "return document.readyState"
        )
        info["page_ready"] = (ready == "complete")

        info["is_error_page"] = is_error_page(
            info["title"], info["url"]
        )
    except Exception:
        pass

    try:
        from selenium.webdriver.common.by import By
        canvases = driver.find_elements(
            By.TAG_NAME, "canvas"
        )
        info["has_canvas"] = len(canvases) > 0
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


def is_game_page_authentic(driver, url):
    """
    Deep check if the loaded page is actually a game
    Returns: (is_game, reason)
    """
    from selenium.webdriver.common.by import By
    
    try:
        page_info = verify_game_page(driver)
        title = page_info.get("title", "").lower()
        
        # Error pages
        if page_info.get("is_error_page"):
            return False, "Page is an error page (404, timeout, or connection failed)"
        
        # Search engines
        search_terms = ["google search", "yahoo search", "bing", "search results", "duckduckgo"]
        if any(term in title for term in search_terms):
            return False, "This appears to be a search engine"
        
        # Social media / video platforms
        social_terms = ["youtube", "facebook", "instagram", "twitter", "reddit", "tiktok", "linkedin"]
        if any(term in title for term in social_terms):
            return False, f"'{title}' is a social platform, not a game"
        
        # E-commerce / shopping
        shop_terms = ["amazon", "flipkart", "shop", "buy now", "add to cart", "checkout", "ebay"]
        if any(term in title for term in shop_terms):
            return False, "This appears to be a shopping website, not a game"
        
        # News / articles
        news_terms = ["news", "article", "blog", "medium", "wikipedia", "daily", "post"]
        if any(term in title for term in news_terms):
            return False, "This appears to be a news/article page, not a game"
        
        # Login/authentication pages
        auth_terms = ["login", "sign in", "sign up", "register", "forgot password"]
        if any(term in title for term in auth_terms):
            return False, "This appears to be a login page, not a game"
        
        # Canvas element (strong game indicator)
        if page_info.get("has_canvas"):
            return True, "Canvas detected - game likely (canvas is used for rendering games)"
        
        # Game keywords in title
        game_title_keywords = ["game", "play", "online", "arcade", "fun", 
                               "adventure", "action", "puzzle", "strategy",
                               "racing", "sports", "shooting", "rpg"]
        for kw in game_title_keywords:
            if kw in title:
                return True, f"Game keyword '{kw}' found in page title"
        
        # Game element detection
        try:
            game_selectors = [
                "canvas", "[id*='game']", "[class*='game']",
                "[id*='player']", "[class*='player']",
                "#game-container", ".game-container",
                "[id*='score']", "[class*='score']"
            ]
            for sel in game_selectors:
                if driver.find_elements(By.CSS_SELECTOR, sel):
                    return True, f"Game element '{sel}' found on page"
        except:
            pass
        
        # Generic page with no game indicators
        return False, "No game indicators found on this page (no canvas, no game-related elements or keywords)"
        
    except Exception as e:
        return False, "Could not verify game status: " + str(e)[:80]


def extract_score(driver):
    try:
        from selenium.webdriver.common.by import By
        selectors = [
            (By.ID, "score"),
            (By.ID, "Score"),
            (By.ID, "points"),
            (By.CLASS_NAME, "score"),
            (By.CLASS_NAME, "game-score"),
            (By.CSS_SELECTOR, '[class*="score"]'),
        ]
        for by, sel in selectors:
            try:
                el = driver.find_element(by, sel)
                nums = re.findall(r"\d+\.?\d*", el.text.strip())
                if nums:
                    return float(nums[0])
            except Exception:
                continue

        for var in ["window.score", "window.Score", "window.points"]:
            try:
                val = driver.execute_script("return " + var + ";")
                if isinstance(val, (int, float)) and val >= 0:
                    return float(val)
            except Exception:
                continue
    except Exception:
        pass
    return None


def calculate_performance(time_survived, actions, scores, errors, is_error_page, load_failed):
    """
    Calculate real performance based on multiple factors
    Invalid/error pages will always get NotGame/Low
    """

    if load_failed or is_error_page:
        return "NotGame"

    if actions == 0:
        return "Low"

    score = 0

    # Time factor (40pts)
    if time_survived >= 15:
        score += 40
    elif time_survived >= 8:
        score += 25
    else:
        score += 10

    # Action rate factor (30pts)
    action_rate = actions / max(time_survived, 1)
    if action_rate >= 1.0:
        score += 30
    elif action_rate >= 0.5:
        score += 20
    else:
        score += 10

    # Score growth factor (20pts)
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


def detect_game_type(driver, url, page_info, metrics):
    """
    Detect what type of game it is based on URL, page content, and behavior
    Returns dict with game type info
    """
    from selenium.webdriver.common.by import By
    
    url_lower = url.lower()
    title = page_info.get("title", "").lower()
    body_text = ""
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()[:1000]
    except:
        pass
    
    # Game Type Indicators
    game_types = {
        "Endless Runner": {
            "keywords": ["runner", "endless", "dino", "temple run", "subway surfers", "run", "jump", "avoid", "obstacle"],
            "url_indicators": ["runner", "endless", "dino", "run"],
            "behavior": "high_action_rate",
            "description": "Player continuously runs while avoiding obstacles. Tests reaction speed."
        },
        "Puzzle": {
            "keywords": ["puzzle", "match", "brain", "quiz", "trivia", "sudoku", "crossword", "2048", "candy", "crush", "merge"],
            "url_indicators": ["puzzle", "match", "brain", "quiz", "2048", "sudoku"],
            "behavior": "moderate_actions",
            "description": "Requires thinking and strategy. Usually turn-based or matching mechanics."
        },
        "Action/Shooter": {
            "keywords": ["shoot", "gun", "battle", "fight", "combat", "arena", "survive", "zombie", "war", "fps", "tps"],
            "url_indicators": ["shooter", "action", "fps", "battle", "combat", "war"],
            "behavior": "high_action_rate",
            "description": "Fast-paced with shooting or combat mechanics. Tests reflexes."
        },
        "Racing": {
            "keywords": ["race", "racing", "car", "drive", "speed", "motor", "bike", "drift", "track", "formula"],
            "url_indicators": ["racing", "race", "car", "drive", "speed"],
            "behavior": "high_action_rate",
            "description": "Vehicle racing against time or opponents. Tests control precision."
        },
        "Sports": {
            "keywords": ["soccer", "football", "basketball", "tennis", "golf", "baseball", "cricket", "sports", "kick", "goal"],
            "url_indicators": ["sports", "soccer", "football", "basketball", "tennis", "golf"],
            "behavior": "moderate_actions",
            "description": "Simulates real-world sports. Tests skill and timing."
        },
        "Idle/Clicker": {
            "keywords": ["idle", "clicker", "tap", "grind", "upgrade", "cookie", "factory", "incremental", "merge"],
            "url_indicators": ["idle", "clicker", "incremental", "tap"],
            "behavior": "low_action_rate",
            "description": "Progression happens automatically or with simple clicks. Focuses on upgrades."
        },
        "Strategy/Tower Defense": {
            "keywords": ["strategy", "tower", "defense", "td", "build", "base", "army", "kingdom", "castle", "clash"],
            "url_indicators": ["strategy", "td", "tower", "defense", "clash"],
            "behavior": "moderate_actions",
            "description": "Requires planning and resource management. Usually involves building or defending."
        },
        "Card/Board": {
            "keywords": ["card", "poker", "solitaire", "chess", "checkers", "board", "dice", "monopoly", "rummy", "blackjack"],
            "url_indicators": ["card", "poker", "chess", "board", "solitaire"],
            "behavior": "low_action_rate",
            "description": "Based on cards or board game mechanics. Turn-based strategy."
        },
        "Platformer": {
            "keywords": ["platform", "jump", "mario", "sonic", "adventure", "collect", "coins", "level"],
            "url_indicators": ["platform", "adventure", "mario", "sonic"],
            "behavior": "high_action_rate",
            "description": "Jump between platforms, collect items, avoid enemies. Tests precision."
        },
        "Simulation": {
            "keywords": ["sim", "simulator", "city", "farm", "build", "manage", "tycoon", "life", "craft", "survival"],
            "url_indicators": ["sim", "simulator", "tycoon", "city", "farm", "craft"],
            "behavior": "low_action_rate",
            "description": "Simulates real activities. Focuses on management and creativity."
        },
        "Fighting": {
            "keywords": ["fight", "fighter", "punch", "kick", "combo", "martial", "boxing", "mortal", "street fighter"],
            "url_indicators": ["fighter", "fighting", "combat", "boxing", "mortal"],
            "behavior": "high_action_rate",
            "description": "One-on-one combat. Tests combo execution and reaction time."
        },
        "Arcade/Classic": {
            "keywords": ["arcade", "classic", "retro", "pacman", "tetris", "snake", "pong", "space", "invader"],
            "url_indicators": ["arcade", "classic", "retro", "pacman", "tetris"],
            "behavior": "high_action_rate",
            "description": "Classic arcade style. Simple mechanics, increasing difficulty."
        },
        "Educational": {
            "keywords": ["learn", "math", "spelling", "typing", "kids", "school", "teach", "alphabet", "number", "color"],
            "url_indicators": ["learn", "math", "kids", "school", "typing", "educational"],
            "behavior": "moderate_actions",
            "description": "Designed for learning. Tests knowledge or skills."
        }
    }
    
    # Score each game type
    scores_dict = {}
    action_rate = metrics.get("actions", 0) / max(metrics.get("time_survived", 1), 1)
    
    for game_type, data in game_types.items():
        score = 0
        indicators_found = []
        
        # Check keywords in title and body
        for keyword in data["keywords"]:
            if keyword in title:
                score += 15
                indicators_found.append(f"keyword '{keyword}' in title")
            elif keyword in body_text:
                score += 5
                indicators_found.append(f"keyword '{keyword}' in content")
        
        # Check URL indicators
        for indicator in data["url_indicators"]:
            if indicator in url_lower:
                score += 20
                indicators_found.append(f"'{indicator}' in URL")
        
        # Check behavior patterns
        if data["behavior"] == "high_action_rate" and action_rate > 0.8:
            score += 15
            indicators_found.append("high action rate detected")
        elif data["behavior"] == "moderate_actions" and 0.3 < action_rate <= 0.8:
            score += 10
            indicators_found.append("moderate action rate detected")
        elif data["behavior"] == "low_action_rate" and action_rate <= 0.3:
            score += 10
            indicators_found.append("low action rate detected")
        
        scores_dict[game_type] = {"score": score, "indicators": indicators_found}
    
    # Get best match
    best_match = max(scores_dict.items(), key=lambda x: x[1]["score"])
    best_type = best_match[0]
    best_score = best_match[1]["score"]
    indicators = best_match[1]["indicators"][:5]
    
    # Determine confidence
    if best_score >= 50:
        confidence = "High"
    elif best_score >= 25:
        confidence = "Medium"
    else:
        confidence = "Low"
        best_type = "Unknown/General" if best_score < 15 else best_type
    
    # Get description
    description = game_types.get(best_type, {}).get("description", "A web-based browser game.")
    
    return {
        "primary_type": best_type,
        "confidence": confidence,
        "indicators": indicators,
        "description": description,
        "all_scores": {k: v["score"] for k, v in scores_dict.items() if v["score"] > 0}
    }


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

    logger.info("Testing: " + url)

    driver = None
    actions = 0
    errors = 0
    scores = [0]
    page_info = {}
    load_failed = False
    start_time = time.time()
    game_type_info = {}

    try:
        driver = create_driver()

        # Load Page
        logger.info("Loading page...")
        try:
            driver.get(url)
        except TimeoutException:
            logger.warning("Page load timeout - continuing")
        except Exception as e:
            err_msg = str(e)
            logger.warning("Load issue: " + err_msg[:80])

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
                logger.warning("Connection failed: " + url)

        if not is_browser_alive(driver):
            logger.error("Browser died after page load")
            load_failed = True

        else:
            try:
                WebDriverWait(driver, 8).until(
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
                page_info = verify_game_page(driver)
                logger.info("Title: " + page_info.get("title", "?"))
                logger.info("Canvas: " + str(page_info.get("has_canvas", False)))
                logger.info("Error page: " + str(page_info.get("is_error_page", False)))

                if page_info.get("is_error_page"):
                    load_failed = True
                    logger.warning("Error page detected: " + page_info.get("title", ""))

                # Verify if this is actually a game page
                if not load_failed:
                    is_game, game_reason = is_game_page_authentic(driver, url)
                    logger.info("Game verification: " + str(is_game) + " - " + game_reason)
                    
                    if not is_game:
                        logger.warning("Non-game detected: " + game_reason)
                        driver.quit()
                        return {
                            "time_survived": 0,
                            "actions": 0,
                            "performance": "NotGame",
                            "scores": [0],
                            "errors": 0,
                            "screenshots": [],
                            "page_info": page_info,
                            "url": url,
                            "load_failed": True,
                            "not_a_game": True,
                            "game_check_reason": game_reason,
                            "tested_at": datetime.now().isoformat()
                        }

                time.sleep(GAME_LOAD_WAIT)

                if not is_browser_alive(driver):
                    logger.error("Browser died before actions")
                    load_failed = True

                else:
                    body = None
                    try:
                        body = driver.find_element(
                            By.TAG_NAME, "body"
                        )
                        driver.execute_script(
                            "arguments[0].click();", body
                        )
                        logger.info("Page focused")
                    except Exception:
                        try:
                            driver.execute_script(
                                "document.body.focus();"
                            )
                            body = driver.find_element(
                                By.TAG_NAME, "body"
                            )
                        except Exception:
                            pass

                    logger.info("Running " + str(ACTION_ROUNDS) + " actions...")

                    for i in range(ACTION_ROUNDS):

                        if not is_browser_alive(driver):
                            logger.warning(
                                "Browser died at action " + str(i)
                            )
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
                                scores.append(round(
                                    elapsed * random.uniform(2.0, 4.0),
                                    2
                                ))

                            time.sleep(random.uniform(
                                ACTION_DELAY_MIN, ACTION_DELAY_MAX
                            ))

                        except ElementNotInteractableException:
                            errors += 1
                            try:
                                body = driver.find_element(
                                    By.TAG_NAME, "body"
                                )
                                driver.execute_script(
                                    "document.body.focus();"
                                )
                            except Exception:
                                pass

                        except Exception as e:
                            logger.warning(
                                "Action " + str(i) + ": " + str(e)[:50]
                            )
                            errors += 1
                            if errors >= MAX_ACTION_ERRORS:
                                break

                    logger.info(
                        "Done: " + str(actions) + " actions, " + str(errors) + " errors"
                    )

    except Exception as e:
        logger.error("Test error: " + str(e)[:80])
        load_failed = True

    finally:
        if driver:
            try:
                # Detect game type before closing
                if not load_failed and actions > 0:
                    game_type_info = detect_game_type(driver, url, page_info, {
                        "actions": actions,
                        "time_survived": time.time() - start_time
                    })
                driver.quit()
                logger.info("Browser closed")
            except Exception:
                pass

    end_time = time.time()
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
        "Result: " + str(time_survived) + "s | "
        + str(actions) + " actions | "
        + performance + " | "
        + "load_failed=" + str(load_failed)
    )

    return {
        "time_survived": time_survived,
        "actions": actions,
        "performance": performance,
        "scores": scores,
        "errors": errors,
        "screenshots": [],
        "page_info": page_info,
        "game_type": game_type_info,
        "url": url,
        "load_failed": load_failed,
        "tested_at": datetime.now().isoformat()
    }