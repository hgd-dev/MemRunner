from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .vocab_store import VocabStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="memrunner", description="Local Memrise Community course automation assistant.")
    parser.add_argument("--env", default=None, help="Path to a .env file. Defaults to .env in the current folder.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("learn", help="Run Learn mode and auto-save new vocab from presentation slides.")
    sub.add_parser("review", help="Run Classic Review mode.")

    speed_parser = sub.add_parser("speed", help="Run Speed Review mode.")
    speed_parser.add_argument("--workers", type=int, default=1, help="Number of browser windows to run.")

    import_parser = sub.add_parser("import-txt", help="Import aligned line-by-line text files into the course vocab database.")
    import_parser.add_argument("prompt_file", help="Front/source prompt text file.")
    import_parser.add_argument("answer_file", help="Back/target answer text file.")
    import_parser.add_argument("--prompt-lang", default=None, help="Optional prompt language/label.")
    import_parser.add_argument("--answer-lang", default=None, help="Optional answer language/label.")

    csv_parser = sub.add_parser("import-csv", help="Import vocab from CSV. Headers: prompt_text, answer_text, prompt_lang, answer_lang.")
    csv_parser.add_argument("csv_file")

    export_parser = sub.add_parser("export-csv", help="Export this course's vocab to CSV.")
    export_parser.add_argument("csv_file")

    sub.add_parser("status", help="Show current config and vocab count.")
    sub.add_parser("ui", help="Launch the local web-style dashboard.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    require_ready = args.command in {"learn", "review", "speed"}
    config = load_config(args.env, require_ready=require_ready)
    store = VocabStore(config.db_path)
    try:
        if args.command == "learn":
            from .modes import learn
            learn.run(config, store)
        elif args.command == "review":
            from .modes import review
            review.run(config, store)
        elif args.command == "speed":
            from .modes import speed
            speed.run(config, workers=args.workers)
        elif args.command == "import-txt":
            if not config.course_id:
                raise RuntimeError("Missing course_id. Open `memrunner ui` and save a Course ID first, or set MEMRISE_COURSE_ID.")
            added = store.import_aligned_txt(
                config.course_id,
                Path(args.prompt_file),
                Path(args.answer_file),
                args.prompt_lang or config.source_label,
                args.answer_lang or config.target_label,
            )
            print(f"Imported or updated {added} aligned vocab pairs into {config.db_path}.")
        elif args.command == "import-csv":
            if not config.course_id:
                raise RuntimeError("Missing course_id. Open `memrunner ui` and save a Course ID first, or set MEMRISE_COURSE_ID.")
            added = store.import_csv(config.course_id, Path(args.csv_file))
            print(f"Imported or updated {added} CSV vocab pairs into {config.db_path}.")
        elif args.command == "export-csv":
            if not config.course_id:
                raise RuntimeError("Missing course_id. Open `memrunner ui` and save a Course ID first, or set MEMRISE_COURSE_ID.")
            count = store.export_csv(config.course_id, Path(args.csv_file))
            print(f"Exported {count} vocab pairs to {args.csv_file}.")
        elif args.command == "status":
            missing = config.missing_required()
            if missing:
                print("Missing settings: " + ", ".join(missing))
                print("Open `memrunner ui` to fill them in, or use .env.")
            print(f"Course ID: {config.course_id}")
            print(f"Source label: {config.source_label}")
            print(f"Target label: {config.target_label}")
            print(f"Database: {config.db_path}")
            print(f"Vocab pairs: {store.count(config.course_id)}")
        elif args.command == "ui":
            from .ui import run_ui
            run_ui(config, store)
    finally:
        store.close()


if __name__ == "__main__":
    main()
