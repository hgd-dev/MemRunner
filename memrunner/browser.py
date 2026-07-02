from __future__ import annotations

import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

from .config import MemRunnerConfig
from .text import clean_text, strip_choice_prefix, normalize_key


NEXT_LABELS = {"continue", "next", "siguiente", "continuar", "comenzar", "start"}
IGNORE_BUTTONS = {"skip", "continue", "next", "start", "restart", "submit", "hint", "i don't know"}
ACCENT_KEYS = {"á", "é", "í", "ó", "ú", "ñ", "ü", "à", "è", "ì", "ò", "ù", "ç"}


def make_driver(config: MemRunnerConfig) -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--start-maximized")
    if config.mute_audio:
        opts.add_argument("--mute-audio")
    if config.headless:
        opts.add_argument("--headless=new")
    return webdriver.Chrome(options=opts)


def auto_login(driver: webdriver.Chrome, config: MemRunnerConfig) -> None:
    driver.get("https://community-courses.memrise.com/signin/")
    wait = WebDriverWait(driver, 25)
    email_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='signinUsernameInput']")))
    pass_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='signinPasswordInput']")))
    for box, value in [(email_box, config.email), (pass_box, config.password)]:
        try:
            box.clear()
        except Exception:
            pass
        box.send_keys(value)
    pass_box.send_keys(Keys.ENTER)
    wait.until(lambda d: "signin" not in d.current_url.lower())


def safe_click(driver: webdriver.Chrome, el) -> bool:
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", el)
        time.sleep(0.02)
    except Exception:
        pass
    try:
        el.click()
        return True
    except Exception:
        pass
    try:
        driver.execute_script("arguments[0].click();", el)
        return True
    except Exception:
        return False


def press_enter(driver: webdriver.Chrome, count: int = 1, interval_s: float = 0.04) -> None:
    for _ in range(max(1, count)):
        sent = False
        try:
            driver.switch_to.active_element.send_keys(Keys.ENTER)
            sent = True
        except Exception:
            pass
        if not sent:
            try:
                ActionChains(driver).send_keys(Keys.ENTER).perform()
                sent = True
            except Exception:
                pass
        if not sent:
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                body.click()
                body.send_keys(Keys.ENTER)
            except Exception:
                pass
        time.sleep(interval_s)


def maybe_click_next(driver: webdriver.Chrome) -> bool:
    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, "button")
    except Exception:
        return False
    for button in buttons:
        try:
            text = clean_text(button.text).casefold()
        except StaleElementReferenceException:
            continue
        if text in NEXT_LABELS:
            return safe_click(driver, button)
    for css in ["button[data-testid='next-button']", "button[data-testid*='next']"]:
        try:
            for button in driver.find_elements(By.CSS_SELECTOR, css):
                if button.is_displayed() and button.is_enabled():
                    return safe_click(driver, button)
        except Exception:
            pass
    return False


def has_visible(driver: webdriver.Chrome, css: str) -> bool:
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, css)
    except Exception:
        return False
    for el in elements:
        try:
            if el.is_displayed():
                return True
        except Exception:
            continue
    return False


def first_nonempty_text(driver: webdriver.Chrome, selectors: list[str], max_tries: int = 2) -> tuple[str | None, str | None]:
    for _ in range(max_tries):
        try:
            for css in selectors:
                for el in driver.find_elements(By.CSS_SELECTOR, css):
                    try:
                        text = clean_text(el.text)
                    except StaleElementReferenceException:
                        continue
                    if text:
                        return text, css
            return None, None
        except StaleElementReferenceException:
            time.sleep(0.03)
    return None, None


def find_prompt_text(driver: webdriver.Chrome, known_keys: set[str]) -> str | None:
    prompt, _ = first_nonempty_text(driver, ["[data-testid*='prompt']", "[data-testid*='Prompt']"])
    if prompt and normalize_key(prompt) in known_keys:
        return prompt

    roots = driver.find_elements(By.CSS_SELECTOR, "[data-testid='testLearnableCard']")
    scopes = roots if roots else [driver]
    candidates: list[str] = []
    for scope in scopes:
        try:
            elements = scope.find_elements(By.CSS_SELECTOR, "[dir='auto']")
        except Exception:
            continue
        for el in elements:
            try:
                text = clean_text(el.text)
            except StaleElementReferenceException:
                continue
            if not text:
                continue
            low = text.casefold()
            if low in IGNORE_BUTTONS:
                continue
            if "type the correct" in low or "type what you hear" in low:
                continue
            candidates.append(text)
    matches = [text for text in candidates if normalize_key(text) in known_keys]
    if matches:
        matches.sort(key=len, reverse=True)
        return matches[0]
    return None


def get_choice_elements(driver: webdriver.Chrome, max_tries: int = 2) -> list[tuple[object, str]]:
    for _ in range(max_tries):
        try:
            roots = driver.find_elements(By.CSS_SELECTOR, "[data-testid='testLearnableCard']")
            root = roots[0] if roots else driver
            output: list[tuple[object, str]] = []
            for el in root.find_elements(By.CSS_SELECTOR, "button"):
                try:
                    text = clean_text(el.text)
                except StaleElementReferenceException:
                    continue
                if not text:
                    continue
                low = text.casefold()
                if low in IGNORE_BUTTONS:
                    continue
                if len(text) == 1 and text in ACCENT_KEYS:
                    continue
                if len(text) > 140:
                    continue
                output.append((el, strip_choice_prefix(text)))
            return output
        except StaleElementReferenceException:
            time.sleep(0.03)
    return []


def find_typing_input(driver: webdriver.Chrome):
    selectors = [
        "input[data-testid='typing-response-input']",
        "input[data-testid*='typing'][type='text']",
        "input[type='text'][enterkeyhint='send']",
        "textarea[data-testid*='typing']",
    ]
    for css in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, css)
        except Exception:
            elements = []
        for el in elements:
            try:
                if el.is_displayed() and el.is_enabled():
                    return el
            except StaleElementReferenceException:
                continue
    return None


def submit_typing_answer(driver: webdriver.Chrome, answer: str) -> bool:
    input_el = find_typing_input(driver)
    if input_el is None:
        return False
    try:
        ActionChains(driver).move_to_element(input_el).click().send_keys(answer).send_keys(Keys.ENTER).perform()
        return True
    except Exception:
        return False


def suggest_choice(answers: list[str], choices: list[tuple[object, str]]):
    answer_keys = {normalize_key(answer) for answer in answers}
    for el, text in choices:
        if normalize_key(text) in answer_keys:
            return el, text
    return None


def is_completed_page(driver: webdriver.Chrome) -> bool:
    try:
        headings = driver.find_elements(By.CSS_SELECTOR, "h1, h2")
    except Exception:
        headings = []
    for heading in headings:
        try:
            text = clean_text(heading.text).casefold()
        except StaleElementReferenceException:
            continue
        if "completed the session" in text or "completado la sesión" in text or "completaste la sesión" in text:
            return True
    return has_visible(driver, "a[href^='/aprender/learn']") or has_visible(driver, "a[href^='/aprender/review']") or has_visible(driver, "a[href^='/aprender/speed']")


def open_link_from_completed_page(driver: webdriver.Chrome, path_prefix: str) -> bool:
    try:
        href = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f"a[href^='{path_prefix}']"))
        ).get_attribute("href")
    except TimeoutException:
        return False
    if not href:
        return False
    if href.startswith("/"):
        href = "https://community-courses.memrise.com" + href
    driver.get(href)
    return True
