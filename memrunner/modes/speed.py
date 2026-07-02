from __future__ import annotations

import time
from multiprocessing import Process
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

from ..browser import auto_login, first_nonempty_text, get_choice_elements, make_driver, safe_click
from ..config import MemRunnerConfig
from ..text import strip_choice_prefix, normalize_key
from ..vocab_store import VocabStore


def _log(worker_id: int, message: str) -> None:
    print(f"[W{worker_id}] {message}", flush=True)


def click_speed_review(driver) -> bool:
    wait = WebDriverWait(driver, 10)
    try:
        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='speedReview']")))
    except TimeoutException:
        return False
    return safe_click(driver, element)


def go_to_course(driver, course_id: str) -> None:
    wait = WebDriverWait(driver, 20)
    link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"a[href='/community/course/{course_id}/']")))
    driver.execute_script("arguments[0].click();", link)
    wait.until(lambda d: f"/community/course/{course_id}/" in d.current_url)


def go_to_speed_review(driver, config: MemRunnerConfig) -> None:
    wait = WebDriverWait(driver, 20)
    primary = f"a[href='/aprender/speed?course_id={config.course_id}']"
    backup = "a[data-tracking-name='course_mode'][data-original-title='Speed review']"
    try:
        button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, primary)))
    except TimeoutException:
        button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, backup)))
    driver.execute_script("arguments[0].click();", button)
    wait.until(lambda d: "aprender/speed" in d.current_url)


def open_speed_review_from_completed_page(driver) -> bool:
    try:
        href = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='/aprender/speed']"))
        ).get_attribute("href")
    except TimeoutException:
        return False
    if not href:
        return False
    if href.startswith("/"):
        href = "https://community-courses.memrise.com" + href
    driver.get(href)
    return True


def _xpath_literal(value: str) -> str:
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    parts = value.split("'")
    return "concat(" + ', "\'", '.join(f"'{part}'" for part in parts) + ")"


def click_choice_by_text(driver, target_text: str, timeout: float = 2.0) -> bool:
    literal = _xpath_literal(target_text.strip())
    xpath = f"//button[.//span[@dir='auto' and normalize-space(.) = {literal}]]"
    end = time.time() + timeout
    while time.time() < end:
        try:
            button = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            return safe_click(driver, button)
        except (StaleElementReferenceException, TimeoutException):
            time.sleep(0.03)
    return False


def click_continue_button(driver, timeout: float = 2.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, "button")
            for button in buttons:
                text = (button.text or "").strip().casefold()
                if text in {"continue", "next", "siguiente", "continuar"}:
                    return safe_click(driver, button)
        except StaleElementReferenceException:
            time.sleep(0.03)
    return False


def _run_worker(worker_id: int, config: MemRunnerConfig) -> None:
    store = VocabStore(config.db_path)
    driver = None
    try:
        while True:
            driver = make_driver(config)
            actions = ActionChains(driver)
            try:
                _log(worker_id, f"Loaded {store.count(config.course_id)} vocab pairs.")
                auto_login(driver, config)
                try:
                    go_to_course(driver, config.course_id)
                    go_to_speed_review(driver, config)
                except Exception:
                    driver.get(config.speed_url)
                time.sleep(3.5)
                _log(worker_id, "Speed assistant running.")
                last_sig = None
                while True:
                    prompt, _ = first_nonempty_text(driver, ["[data-testid*='prompt']"])
                    if not prompt:
                        if click_speed_review(driver):
                            _log(worker_id, "[ROUND] Finished speed review.")
                            click_continue_button(driver)
                            open_speed_review_from_completed_page(driver)
                            time.sleep(3.5)
                            continue
                        _log(worker_id, "No prompt; restarting browser.")
                        break
                    choices = get_choice_elements(driver)
                    cleaned = [(el, strip_choice_prefix(text)) for el, text in choices if 1 < len(text) <= 120]
                    if len(cleaned) < 2:
                        time.sleep(config.action_delay_s)
                        continue
                    sig = (prompt, tuple(text for _, text in cleaned))
                    if sig == last_sig:
                        time.sleep(config.action_delay_s)
                        continue
                    last_sig = sig
                    answers = store.answers_for(config.course_id, prompt)
                    answer_keys = {normalize_key(answer) for answer in answers}
                    target = next(((el, text) for el, text in cleaned if normalize_key(text) in answer_keys), None)
                    if target:
                        click_choice_by_text(driver, target[1]) or safe_click(driver, target[0])
                    actions.send_keys(Keys.ENTER).perform()
                    time.sleep(config.action_delay_s)
            except KeyboardInterrupt:
                break
            except Exception as exc:
                _log(worker_id, f"Worker error: {exc}")
                time.sleep(2)
            finally:
                if driver is not None:
                    try:
                        driver.quit()
                    except Exception:
                        pass
    finally:
        store.close()


def run(config: MemRunnerConfig, workers: int = 1) -> None:
    workers = max(1, int(workers))
    processes: list[Process] = []
    for worker_id in range(1, workers + 1):
        process = Process(target=_run_worker, args=(worker_id, config))
        process.start()
        processes.append(process)
    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        print("Stopping all speed workers.", flush=True)
        for process in processes:
            if process.is_alive():
                process.terminate()
        for process in processes:
            process.join()
