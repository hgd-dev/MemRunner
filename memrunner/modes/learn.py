from __future__ import annotations

import time
from selenium.common.exceptions import WebDriverException

from ..browser import (
    auto_login,
    find_prompt_text,
    get_choice_elements,
    is_completed_page,
    make_driver,
    maybe_click_next,
    open_link_from_completed_page,
    press_enter,
    safe_click,
    submit_typing_answer,
    suggest_choice,
    find_typing_input,
)
from ..config import MemRunnerConfig
from ..presentation import extract_presentation_pair, is_listening_question, is_presentation_slide
from ..vocab_store import VocabStore


def run(config: MemRunnerConfig, store: VocabStore) -> None:
    while True:
        driver = make_driver(config)
        last_action_time = time.time()
        try:
            print("Opening browser for Learn mode. Press Ctrl+C to stop.")
            auto_login(driver, config)
            driver.get(config.learn_url)
            print(f"Loaded {store.count(config.course_id)} vocab pairs. Learn assistant running.")
            while True:
                time.sleep(config.action_delay_s)
                known_keys = store.known_keys(config.course_id)

                if is_completed_page(driver):
                    print("[COMPLETE] Moving to next learn round.")
                    if not open_link_from_completed_page(driver, "/aprender/learn"):
                        press_enter(driver)
                        maybe_click_next(driver)
                    last_action_time = time.time()
                    continue

                if is_presentation_slide(driver):
                    pair = extract_presentation_pair(driver, config.source_label, config.target_label)
                    if pair:
                        added = store.add_pair(
                            config.course_id,
                            pair[0],
                            pair[1],
                            config.source_label,
                            config.target_label,
                            source="learn-slide",
                        )
                        if added:
                            print(f"[LEARNED] {pair[0]!r} -> {pair[1]!r}")
                    press_enter(driver)
                    if is_presentation_slide(driver):
                        maybe_click_next(driver)
                    last_action_time = time.time()
                    continue

                if is_listening_question(driver):
                    press_enter(driver, count=2, interval_s=0.08)
                    maybe_click_next(driver)
                    last_action_time = time.time()
                    continue

                prompt = find_prompt_text(driver, known_keys)
                if prompt:
                    answers = store.answers_for(config.course_id, prompt)
                    if answers and find_typing_input(driver) is not None:
                        if submit_typing_answer(driver, answers[0]):
                            print(f"[TYPED] {prompt!r} -> {answers[0]!r}")
                            last_action_time = time.time()
                            continue
                    choices = get_choice_elements(driver)
                    suggestion = suggest_choice(answers, choices) if answers and choices else None
                    if suggestion is not None:
                        element, text = suggestion
                        if safe_click(driver, element):
                            print(f"[CLICK] {prompt!r} -> {text!r}")
                            last_action_time = time.time()
                            continue

                if time.time() - last_action_time > config.idle_timeout_s:
                    print("[IDLE] Sending Enter.")
                    press_enter(driver)
                    last_action_time = time.time()
                    if time.time() - last_action_time > config.idle_timeout_s * 3:
                        driver.refresh()
        except KeyboardInterrupt:
            driver.quit()
            raise
        except WebDriverException as exc:
            print(f"WebDriver error: {exc}")
        except Exception as exc:
            print(f"Learn mode error: {exc}")
        finally:
            try:
                driver.quit()
            except Exception:
                pass
        print("Restarting Learn browser session in 2 seconds.")
        time.sleep(2)
