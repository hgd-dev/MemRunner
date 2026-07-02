from __future__ import annotations

import os
import signal
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any

from flask import Flask, Response, redirect, render_template_string, request, url_for

from .config import APP_DIR, LOG_PATH, RUN_STATE_PATH, MemRunnerConfig, load_config, save_dashboard_settings
from .vocab_store import VocabStore

TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MemRunner Dashboard</title>
  <style>
    :root { --bg:#f5f5f7; --ink:#171717; --muted:#6b7280; --card:#fff; --line:#ddd; --good:#0f766e; --bad:#b91c1c; }
    body { font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 0; background: var(--bg); color: var(--ink); }
    header { background: var(--ink); color: white; padding: 24px 30px; }
    header h1 { margin: 0 0 6px; }
    header p { margin: 0; opacity: .85; }
    main { max-width: 1180px; margin: 24px auto; padding: 0 18px 40px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(285px, 1fr)); gap: 16px; align-items: start; }
    .card { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 18px; box-shadow: 0 1px 2px rgba(0,0,0,.05); }
    .wide { grid-column: 1 / -1; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, button, select { font: inherit; }
    input[type=text], input[type=password], input[type=number], select { width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #cfcfcf; border-radius: 10px; background: white; }
    input[type=checkbox] { transform: translateY(1px); }
    button { border: 0; border-radius: 10px; padding: 10px 14px; background: var(--ink); color: white; cursor: pointer; margin: 8px 6px 0 0; }
    button.secondary { background: #555; }
    button.danger { background: var(--bad); }
    button:disabled { background:#aaa; cursor:not-allowed; }
    .muted { color: var(--muted); font-size: .94rem; }
    .pill { display:inline-block; padding:4px 8px; border-radius:999px; font-size:.85rem; background:#eee; }
    .ok { color: var(--good); font-weight: 700; }
    .bad { color: var(--bad); font-weight: 700; }
    table { width: 100%; border-collapse: collapse; }
    td, th { border-bottom: 1px solid #eee; padding: 8px; text-align: left; vertical-align: top; }
    pre { background:#101010; color:#e5e5e5; padding:14px; border-radius:12px; overflow:auto; max-height:300px; white-space:pre-wrap; }
    .row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
    .two { display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    @media (max-width: 720px) { .two { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
<header>
  <h1>MemRunner</h1>
  <p>A local app-style dashboard for course setup, vocab, runs, and logs.</p>
</header>
<main>
  <div class="grid">
    <section class="card">
      <h2>Readiness</h2>
      {% if ready %}
        <p class="ok">Ready to run.</p>
      {% else %}
        <p class="bad">Missing: {{ missing|join(', ') }}</p>
      {% endif %}
      <p><strong>Course:</strong> {{ config.course_id or 'Not set' }}</p>
      <p><strong>Labels:</strong> {{ config.source_label }} → {{ config.target_label }}</p>
      <p><strong>Database:</strong> {{ config.db_path }}</p>
      <p><strong>Vocab pairs:</strong> {{ count }}</p>
      <p><strong>Run status:</strong> {% if running %}<span class="ok">Running PID {{ run_state.pid }}</span>{% else %}<span class="pill">Stopped</span>{% endif %}</p>
      <p class="muted">Everything is saved locally on this computer. The dashboard is not a public website.</p>
    </section>

    <section class="card">
      <h2>Run controls</h2>
      <form method="post" action="{{ url_for('run_mode') }}">
        <label>Mode</label>
        <select name="mode">
          <option value="learn">Learn new words</option>
          <option value="review">Classic review</option>
          <option value="speed">Speed review</option>
        </select>
        <label>Speed-review browser windows</label>
        <input name="workers" type="number" min="1" max="8" value="1">
        <button {% if not ready or running %}disabled{% endif %}>Start</button>
      </form>
      <form method="post" action="{{ url_for('stop_run') }}">
        <button class="danger" {% if not running %}disabled{% endif %}>Stop current run</button>
      </form>
      <p class="muted">Runs launch as local background processes and write to the log panel below.</p>
    </section>

    <section class="card wide">
      <h2>Settings</h2>
      <form method="post" action="{{ url_for('save_settings') }}">
        <div class="two">
          <div>
            <label>Memrise email</label>
            <input name="email" type="text" autocomplete="username" value="{{ config.email }}" placeholder="you@example.com">
          </div>
          <div>
            <label>Memrise password</label>
            <input name="password" type="password" autocomplete="current-password" placeholder="Leave blank to keep saved password">
          </div>
          <div>
            <label>Course ID or course home link</label>
            <input name="course_id" type="text" value="{{ config.course_id }}" placeholder="1234567 or https://community-courses.memrise.com/community/course/1234567/...">
            <p class="muted">Paste either the raw ID or the full copied course URL. MemRunner will save just the ID.</p>
          </div>
          <div>
            <label>Vocab database path</label>
            <input name="db_path" type="text" value="{{ config.db_path }}">
          </div>
          <div>
            <label>Prompt/source label</label>
            <input name="source_label" type="text" value="{{ config.source_label }}" placeholder="Spanish, French, Term, Front...">
          </div>
          <div>
            <label>Answer/target label</label>
            <input name="target_label" type="text" value="{{ config.target_label }}" placeholder="English, Definition, Back...">
          </div>
          <div>
            <label>Action delay seconds</label>
            <input name="action_delay_s" type="number" step="0.01" min="0" value="{{ config.action_delay_s }}">
          </div>
          <div>
            <label>Idle timeout seconds</label>
            <input name="idle_timeout_s" type="number" step="0.1" min="0.5" value="{{ config.idle_timeout_s }}">
          </div>
        </div>
        <p class="row">
          <label><input name="mute_audio" type="checkbox" {% if config.mute_audio %}checked{% endif %}> Mute browser audio</label>
          <label><input name="headless" type="checkbox" {% if config.headless %}checked{% endif %}> Headless browser</label>
        </p>
        <button>Save settings</button>
      </form>
      <p class="muted">For normal users, this replaces manual .env editing. Advanced users can still use .env overrides.</p>
    </section>

    <section class="card">
      <h2>Import aligned TXT</h2>
      <form method="post" action="{{ url_for('import_txt') }}">
        <label>Prompt/source file path</label>
        <input name="prompt_file" type="text" placeholder="data/spanish.txt">
        <label>Answer/target file path</label>
        <input name="answer_file" type="text" placeholder="data/english.txt">
        <button {% if not config.course_id %}disabled{% endif %}>Import TXT</button>
      </form>
    </section>

    <section class="card">
      <h2>Import CSV</h2>
      <form method="post" action="{{ url_for('import_csv') }}">
        <label>CSV path</label>
        <input name="csv_file" type="text" value="data/sample_spanish_english.csv">
        <button {% if not config.course_id %}disabled{% endif %}>Import CSV</button>
      </form>
      <p class="muted">CSV headers: prompt_text, answer_text, prompt_lang, answer_lang.</p>
    </section>

    <section class="card">
      <h2>Export vocab</h2>
      <form method="post" action="{{ url_for('export_csv') }}">
        <label>Output path</label>
        <input name="csv_file" type="text" value="vocab_export.csv">
        <button {% if not config.course_id %}disabled{% endif %}>Export CSV</button>
      </form>
    </section>

    <section class="card wide">
      <h2>Log</h2>
      <form method="post" action="{{ url_for('clear_log') }}"><button class="secondary">Clear log</button></form>
      <pre>{{ log_text or 'No logs yet.' }}</pre>
    </section>

    <section class="card wide">
      <h2>Recent vocab</h2>
      <table>
        <tr><th>Prompt</th><th>Answer</th><th>Language</th><th>Source</th></tr>
        {% for pair in pairs %}
        <tr><td>{{ pair.prompt_text }}</td><td>{{ pair.answer_text }}</td><td>{{ pair.prompt_lang }} → {{ pair.answer_lang }}</td><td>{{ pair.source }}</td></tr>
        {% endfor %}
      </table>
    </section>
  </div>
</main>
</body>
</html>
"""


def _store_for(config: MemRunnerConfig) -> VocabStore:
    return VocabStore(config.db_path)


def _read_run_state() -> dict[str, Any]:
    if not RUN_STATE_PATH.exists():
        return {}
    try:
        import json
        return json.loads(RUN_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_run_state(state: dict[str, Any]) -> None:
    import json
    APP_DIR.mkdir(parents=True, exist_ok=True)
    RUN_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _is_pid_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _tail_log(max_chars: int = 12000) -> str:
    if not LOG_PATH.exists():
        return ""
    text = LOG_PATH.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:]


def run_ui(_config: MemRunnerConfig | None = None, _store: VocabStore | None = None, host: str = "127.0.0.1", port: int = 7860) -> None:
    app = Flask(__name__)

    @app.get("/")
    def index() -> Any:
        config = load_config(require_ready=False)
        run_state = _read_run_state()
        running = _is_pid_running(run_state.get("pid"))
        with _store_for(config) as store:  # type: ignore[attr-defined]
            pairs = list(store.all_pairs(config.course_id))[-50:] if config.course_id else []
            pairs.reverse()
            count = store.count(config.course_id) if config.course_id else 0
        missing = config.missing_required()
        return render_template_string(
            TEMPLATE,
            config=config,
            count=count,
            pairs=pairs,
            ready=not missing,
            missing=missing,
            running=running,
            run_state=run_state,
            log_text=_tail_log(),
        )

    @app.post("/settings")
    def save_settings() -> Response:
        password = request.form.get("password", "")
        data = dict(request.form)
        data["password"] = password if password else "__KEEP__"
        data["headless"] = "headless" in request.form
        data["mute_audio"] = "mute_audio" in request.form
        save_dashboard_settings(data)
        return redirect(url_for("index"))

    @app.post("/run")
    def run_mode() -> Response:
        config = load_config(require_ready=True)
        state = _read_run_state()
        if _is_pid_running(state.get("pid")):
            return redirect(url_for("index"))
        mode = request.form.get("mode", "learn")
        workers = request.form.get("workers", "1")
        cmd = [sys.executable, "-m", "memrunner.cli", mode]
        if mode == "speed":
            cmd.extend(["--workers", workers])
        APP_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(f"\n--- Starting {mode} ---\n")
            log_file.flush()
            proc = subprocess.Popen(cmd, cwd=Path.cwd(), stdout=log_file, stderr=subprocess.STDOUT)
        _write_run_state({"pid": proc.pid, "mode": mode, "command": cmd})
        return redirect(url_for("index"))

    @app.post("/stop")
    def stop_run() -> Response:
        state = _read_run_state()
        pid = state.get("pid")
        if _is_pid_running(pid):
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False)
                else:
                    os.kill(pid, signal.SIGTERM)
            except Exception as exc:
                APP_DIR.mkdir(parents=True, exist_ok=True)
                with LOG_PATH.open("a", encoding="utf-8") as f:
                    f.write(f"\n[dashboard] Stop failed: {exc}\n")
        try:
            RUN_STATE_PATH.unlink()
        except FileNotFoundError:
            pass
        return redirect(url_for("index"))

    @app.post("/import-txt")
    def import_txt() -> Response:
        config = load_config(require_ready=False)
        prompt_file = request.form.get("prompt_file", "")
        answer_file = request.form.get("answer_file", "")
        if config.course_id and prompt_file and answer_file:
            with _store_for(config) as store:  # type: ignore[attr-defined]
                store.import_aligned_txt(config.course_id, prompt_file, answer_file, config.source_label, config.target_label)
        return redirect(url_for("index"))

    @app.post("/import-csv")
    def import_csv() -> Response:
        config = load_config(require_ready=False)
        csv_file = request.form.get("csv_file", "")
        if config.course_id and csv_file:
            with _store_for(config) as store:  # type: ignore[attr-defined]
                store.import_csv(config.course_id, csv_file)
        return redirect(url_for("index"))

    @app.post("/export-csv")
    def export_csv() -> Response:
        config = load_config(require_ready=False)
        csv_file = request.form.get("csv_file", "vocab_export.csv")
        if config.course_id and csv_file:
            with _store_for(config) as store:  # type: ignore[attr-defined]
                store.export_csv(config.course_id, csv_file)
        return redirect(url_for("index"))

    @app.post("/clear-log")
    def clear_log() -> Response:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        LOG_PATH.write_text("", encoding="utf-8")
        return redirect(url_for("index"))

    url = f"http://{host}:{port}"
    print(f"Opening MemRunner dashboard at {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    app.run(host=host, port=port, debug=False)
