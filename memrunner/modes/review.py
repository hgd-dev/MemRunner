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
    safe_click,
    submit_typing_answer,
    suggest_choice,
    find_typing_input,
)
from ..config import MemRunnerConfig
from ..vocab_store import VocabStore


def run(config: MemRunnerConfig, store: VocabStore) -> None:
    while True:
        driver = make_driver(config)
        try:
            print("Opening browser for Review mode. Press Ctrl+C to stop.")
            auto_login(driver, config)
            driver.get(config.review_url)
            print(f"Loaded {store.count(config.course_id)} vocab pairs. Review assistant running.")
            while True:
                time.sleep(config.action_delay_s)
                if is_completed_page(driver):
                    print("[COMPLETE] Moving to next review round.")
                    if not open_link_from_completed_page(driver, "/aprender/review"):
                        maybe_click_next(driver)
                    continue

                known_keys = store.known_keys(config.course_id)
                prompt = find_prompt_text(driver, known_keys)
                if prompt:
                    answers = store.answers_for(config.course_id, prompt)
                    if answers and find_typing_input(driver) is not None:
                        if submit_typing_answer(driver, answers[0]):
                            print(f"[TYPED] {prompt!r} -> {answers[0]!r}")
                            continue
                    choices = get_choice_elements(driver)
                    suggestion = suggest_choice(answers, choices) if answers and choices else None
                    if suggestion is not None:
                        element, text = suggestion
                        if safe_click(driver, element):
                            print(f"[CLICK] {prompt!r} -> {text!r}")
                            continue

                maybe_click_next(driver)
        except KeyboardInterrupt:
            driver.quit()
            raise
        except WebDriverException as exc:
            print(f"WebDriver error: {exc}")
        except Exception as exc:
            print(f"Review mode error: {exc}")
        finally:
            try:
                driver.quit()
            except Exception:
                pass
        print("Restarting Review browser session in 2 seconds.")
        time.sleep(2)
