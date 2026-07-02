from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .text import clean_text, normalize_key


@dataclass(frozen=True)
class VocabPair:
    prompt_text: str
    answer_text: str
    prompt_lang: str = "source"
    answer_lang: str = "target"
    course_id: str = "default"
    source: str = "manual"


class VocabStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "VocabStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vocab_pairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                prompt_text TEXT NOT NULL,
                answer_text TEXT NOT NULL,
                prompt_key TEXT NOT NULL,
                answer_key TEXT NOT NULL,
                prompt_lang TEXT NOT NULL DEFAULT 'source',
                answer_lang TEXT NOT NULL DEFAULT 'target',
                source TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(course_id, prompt_key, answer_key)
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_vocab_prompt ON vocab_pairs(course_id, prompt_key)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_vocab_answer ON vocab_pairs(course_id, answer_key)")
        self.conn.commit()

    def add_pair(
        self,
        course_id: str,
        prompt_text: str,
        answer_text: str,
        prompt_lang: str = "source",
        answer_lang: str = "target",
        source: str = "manual",
    ) -> bool:
        prompt = clean_text(prompt_text)
        answer = clean_text(answer_text)
        if not prompt or not answer:
            return False
        cur = self.conn.execute(
            """
            INSERT INTO vocab_pairs(course_id, prompt_text, answer_text, prompt_key, answer_key, prompt_lang, answer_lang, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(course_id, prompt_key, answer_key)
            DO UPDATE SET last_seen = CURRENT_TIMESTAMP
            """,
            (course_id, prompt, answer, normalize_key(prompt), normalize_key(answer), prompt_lang, answer_lang, source),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def import_aligned_txt(
        self,
        course_id: str,
        prompt_path: str | Path,
        answer_path: str | Path,
        prompt_lang: str = "source",
        answer_lang: str = "target",
        source: str = "txt-import",
    ) -> int:
        prompts = _load_lines(prompt_path)
        answers = _load_lines(answer_path)
        if len(prompts) != len(answers):
            raise ValueError(f"Line count mismatch: {prompt_path} has {len(prompts)} lines, {answer_path} has {len(answers)} lines.")
        added = 0
        for prompt, answer in zip(prompts, answers):
            if self.add_pair(course_id, prompt, answer, prompt_lang, answer_lang, source):
                added += 1
        return added

    def import_csv(self, course_id: str, csv_path: str | Path, source: str = "csv-import") -> int:
        added = 0
        with Path(csv_path).open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                prompt = row.get("prompt_text") or row.get("prompt") or row.get("source") or ""
                answer = row.get("answer_text") or row.get("answer") or row.get("target") or ""
                prompt_lang = row.get("prompt_lang") or row.get("source_lang") or "source"
                answer_lang = row.get("answer_lang") or row.get("target_lang") or "target"
                if self.add_pair(course_id, prompt, answer, prompt_lang, answer_lang, source):
                    added += 1
        return added

    def export_csv(self, course_id: str, csv_path: str | Path) -> int:
        rows = list(self.all_pairs(course_id))
        with Path(csv_path).open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["course_id", "prompt_text", "answer_text", "prompt_lang", "answer_lang", "source"])
            for pair in rows:
                writer.writerow([pair.course_id, pair.prompt_text, pair.answer_text, pair.prompt_lang, pair.answer_lang, pair.source])
        return len(rows)

    def all_pairs(self, course_id: str) -> Iterable[VocabPair]:
        cur = self.conn.execute(
            """
            SELECT course_id, prompt_text, answer_text, prompt_lang, answer_lang, source
            FROM vocab_pairs
            WHERE course_id = ?
            ORDER BY id ASC
            """,
            (course_id,),
        )
        for course_id, prompt, answer, prompt_lang, answer_lang, source in cur.fetchall():
            yield VocabPair(prompt, answer, prompt_lang, answer_lang, course_id, source)

    def answers_for(self, course_id: str, prompt: str) -> list[str]:
        key = normalize_key(prompt)
        if not key:
            return []
        answers: list[str] = []
        for sql, params in [
            ("SELECT answer_text FROM vocab_pairs WHERE course_id = ? AND prompt_key = ?", (course_id, key)),
            ("SELECT prompt_text FROM vocab_pairs WHERE course_id = ? AND answer_key = ?", (course_id, key)),
        ]:
            cur = self.conn.execute(sql, params)
            for (text,) in cur.fetchall():
                cleaned = clean_text(text)
                if cleaned and cleaned not in answers:
                    answers.append(cleaned)
        return answers

    def known_keys(self, course_id: str) -> set[str]:
        cur = self.conn.execute(
            "SELECT prompt_key FROM vocab_pairs WHERE course_id = ? UNION SELECT answer_key FROM vocab_pairs WHERE course_id = ?",
            (course_id, course_id),
        )
        return {row[0] for row in cur.fetchall()}

    def count(self, course_id: str) -> int:
        cur = self.conn.execute("SELECT COUNT(*) FROM vocab_pairs WHERE course_id = ?", (course_id,))
        return int(cur.fetchone()[0])


def _load_lines(path: str | Path) -> list[str]:
    raw = Path(path).read_text(encoding="utf-8").splitlines()
    return [clean_text(line) for line in raw if clean_text(line)]
