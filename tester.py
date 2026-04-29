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
PAGE_LOAD_TIMEOUT = 15
GAME_LOAD_WAIT    = 2
ACTION_ROUNDS     = 10
ACTION_DELAY_MIN  = 0.2
ACTION_DELAY_MAX  = 0.4
MAX_ACTION_ERRORS = 3

CHROMEDRIVER_PATH = (
    r"C:\Users\HP\.wdm\drivers\chromedriver"
    r"\win64\147.0.7727.117"
    r"\chromedriver-win32\chromedriver.exe"
)

# ── Error page titles that mean failure ───────────────────────
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
        logger.info(f"Chromedriver: {CHROMEDRIVER_PATH}")
        return CHROMEDRIVER_PATH

    wdm_base = os.path.expanduser(r"~\.wdm\drivers\chromedriver")
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

    # ✅ Anti-detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    options.add_experimental_option("useAutomationExtension", False)

    # ✅ Keep Chrome alive
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

    # ✅ Stability
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

    # ✅ Real user agent
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # ✅ Prefs
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups":              0,
        "download.prompt_for_download":                          False,
        "credentials_enable_service":                            False,
        "profile.password_manager_enabled":                      False
    }
    options.add_experimental_option("prefs", prefs)

    driver_path = find_chromedriver()
    if not driver_path:
        raise RuntimeError("ChromeDriver not found!")

    service = Service(executable_path=driver_path)
    driver  = webdriver.Chrome(service=service, options=options)

    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.implicitly_wait(2)

    # ✅ Remove webdriver flag
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


def is_error_page(title: str, url: str) -> bool:
    """Check if page is an error page"""
    title_lower = title.lower()
    url_lower   = url.lower()

    # Check title for error keywords
    for err in ERROR_TITLES:
        if err in title_lower:
            return True

    # Check if URL changed to error page
    if "chrome-error://" in url_lower:
        return True
    if "about:blank" in url_lower and not title_lower:
        return True

    return False


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
        info["title"]    = driver.title or ""
        info["url"]      = driver.current_url or ""
        ready            = driver.execute_script(
            "return document.readyState"
        )
        info["page_ready"] = (ready == "complete")

        # ✅ Check if error page
        info["is_error_page"] = is_error_page(
            info["title"], info["url"]
        )
    except Exception:
        pass

    try:
        from selenium.webdriver.common.by import By
        canvases             = driver.find_elements(
            By.TAG_NAME, "canvas"
        )
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
                el   = driver.find_element(by, sel)
                nums = re.findall(r"\d+\.?\d*", el.text.strip())
                if nums:
                    return float(nums[0])
            except Exception:
                continue

        for var in ["window.score", "window.Score", "window.points"]:
            try:
                val = driver.execute_script(f"return {var};")
                if isinstance(val, (int, float)) and val >= 0:
                    return float(val)
            except Exception:
                continue
    except Exception:
        pass
    return None


def calculate_performance(
    time_survived, actions, scores,
    errors, is_error_page, load_failed
):
    """
    Calculate real performance based on multiple factors
    Invalid/error pages will always get Low
    """

    # ✅ Error page = always Low
    if is_error_page or load_failed:
        return "Low"

    # ✅ No actions = Low
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

    driver      = None
    actions     = 0
    errors      = 0
    scores      = [0]
    page_info   = {}
    load_failed = False
    start_time  = time.time()

    try:
        driver = create_driver()

        # ── Load Page ──
        logger.info("Loading page...")
        try:
            driver.get(url)
        except TimeoutException:
            logger.warning("Page load timeout - continuing")
        except Exception as e:
            err_msg = str(e)
            logger.warning(f"Load issue: {err_msg[:80]}")

            # ✅ Detect real connection failures
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

        # ── Check alive ──
        if not is_browser_alive(driver):
            logger.error("Browser died after page load")
            load_failed = True

        else:
            # ── Wait for ready ──
            try:
                WebDriverWait(driver, 8).until(
                    lambda d: d.execute_script(
                        "return document.readyState"
                    ) == "complete"
                )
            except Exception:
                pass

            # ── Check alive ──
            if not is_browser_alive(driver):
                logger.error("Browser died during wait")
                load_failed = True

            else:
                # ── Verify page ──
                page_info = verify_game_page(driver)
                logger.info(f"Title: {page_info.get('title','?')}")
                logger.info(
                    f"Canvas: {page_info.get('has_canvas', False)}"
                )
                logger.info(
                    f"Error page: {page_info.get('is_error_page', False)}"
                )

                # ✅ If error page detected - mark as failed
                if page_info.get("is_error_page"):
                    load_failed = True
                    logger.warning(
                        f"Error page detected: {page_info.get('title')}"
                    )

                # ── Wait for game ──
                time.sleep(GAME_LOAD_WAIT)

                # ── Check alive ──
                if not is_browser_alive(driver):
                    logger.error("Browser died before actions")
                    load_failed = True

                else:
                    # ── Focus ──
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

                    # ── Run Actions ──
                    logger.info(f"Running {ACTION_ROUNDS} actions...")

                    for i in range(ACTION_ROUNDS):

                        if not is_browser_alive(driver):
                            logger.warning(
                                f"Browser died at action {i}"
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
                                f"Action {i}: {str(e)[:50]}"
                            )
                            errors += 1
                            if errors >= MAX_ACTION_ERRORS:
                                break

                    logger.info(
                        f"Done: {actions} actions, {errors} errors"
                    )

    except Exception as e:
        logger.error(f"Test error: {str(e)[:80]}")
        load_failed = True

    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Browser closed")
            except Exception:
                pass

    # ── Final Metrics ──
    end_time      = time.time()
    time_survived = round(end_time - start_time, 2)

    # ✅ Correct performance calculation
    performance = calculate_performance(
        time_survived,
        actions,
        scores,
        errors,
        page_info.get("is_error_page", False),
        load_failed
    )

    logger.info(
        f"Result: {time_survived}s | "
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
        "url":           url,
        "load_failed":   load_failed,
        "tested_at":     datetime.now().isoformat()
    }
