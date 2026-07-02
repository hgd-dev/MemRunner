from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException

from .text import clean_text


def is_presentation_slide(driver) -> bool:
    try:
        cards = driver.find_elements(By.CSS_SELECTOR, "[data-testid='presentationLearnableCard']")
    except Exception:
        return False
    for card in cards:
        try:
            if card.is_displayed():
                return True
        except StaleElementReferenceException:
            continue
    return False


def extract_text_after_label(card, label_text: str) -> str | None:
    label_text = label_text.casefold()
    try:
        labels = card.find_elements(By.CSS_SELECTOR, "label")
    except Exception:
        labels = []
    for label in labels:
        try:
            text = clean_text(label.text).casefold()
        except Exception:
            continue
        if label_text not in text:
            continue
        for xpath in [
            "./following-sibling::*[self::h1 or self::h2 or self::h3 or self::div][1]",
            "./ancestor::div[1]/*[self::h1 or self::h2 or self::h3 or self::div][normalize-space()][1]",
            "./ancestor::div[1]/following-sibling::div[1]/*[self::h1 or self::h2 or self::h3 or self::div][normalize-space()][1]",
        ]:
            try:
                elements = label.find_elements(By.XPATH, xpath)
            except Exception:
                elements = []
            for element in elements:
                try:
                    value = clean_text(element.text)
                except Exception:
                    continue
                if value and value.casefold() not in {"next", "continue", "siguiente", "continuar"}:
                    return value
    return None


def extract_presentation_pair(driver, source_label: str, target_label: str) -> tuple[str, str] | None:
    try:
        cards = driver.find_elements(By.CSS_SELECTOR, "[data-testid='presentationLearnableCard']")
    except Exception:
        cards = []
    for card in cards:
        try:
            if not card.is_displayed():
                continue
        except Exception:
            continue
        source_value = extract_text_after_label(card, source_label)
        target_value = extract_text_after_label(card, target_label)
        if source_value and target_value:
            return source_value, target_value
        try:
            lines = [clean_text(line) for line in (card.get_attribute("innerText") or card.text or "").splitlines() if clean_text(line)]
        except StaleElementReferenceException:
            continue
        source_idx = target_idx = None
        for i, line in enumerate(lines):
            low = line.casefold()
            if source_idx is None and source_label.casefold() in low:
                source_idx = i
            if target_idx is None and target_label.casefold() in low:
                target_idx = i
        if source_idx is not None and target_idx is not None and source_idx < target_idx:
            source_candidates = lines[source_idx + 1:target_idx]
            target_candidates = [x for x in lines[target_idx + 1:] if x.casefold() not in {"next", "continue", "siguiente", "continuar"}]
            if source_candidates and target_candidates:
                return source_candidates[0], target_candidates[0]
    return None


def is_listening_question(driver) -> bool:
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid='promptAudio'], [data-testid='audioPlayer']")
        for element in elements:
            try:
                if element.is_displayed():
                    return True
            except StaleElementReferenceException:
                continue
    except Exception:
        pass
    try:
        for heading in driver.find_elements(By.CSS_SELECTOR, "h1, h2, [data-testid*='prompt']"):
            try:
                if "type what you hear" in clean_text(heading.text).casefold():
                    return True
            except StaleElementReferenceException:
                continue
    except Exception:
        pass
    return False
