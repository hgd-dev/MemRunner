# MemRunner

The official repository for MemRunner, a local desktop-style automation assistant tool for navigating and completing Memrise Community Courses. It provides a simple dashboard for running course practice modes, managing vocabulary, and automating repeated question-answering sessions from your own computer.

MemRunner is designed for ease of use for all users: after installation, you can open a local dashboard, enter your course information, import vocabulary, and start a practice mode with buttons.

## Features

* Local dashboard interface
* Course setup using either a raw course ID or a full Memrise course link
* Learn mode
* Classic review mode
* Speed review mode
* Multi-window speed review support
* Vocabulary import from aligned `.txt` files
* Vocabulary import/export through `.csv`
* Course-agnostic vocabulary storage
* Works beyond one language pair
* Local settings storage
* Live logs in the dashboard
* Start/stop controls from the dashboard
* Optional `.env` support for advanced users

## Important Note

MemRunner runs locally on your own computer. Your login information and course settings are not sent to a third-party server by MemRunner.

This project is an independent tool and is not affiliated with, endorsed by, or sponsored by Memrise.

Use responsibly and only in ways allowed by the services you access.

## Installation

### 1. Download the project

Download or clone this repository.

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

Or download the ZIP from GitHub, unzip it, and open the project folder.

### 2. Install Python

Install Python 3.10 or newer.

You can check your version with:

```bash
python --version
```

or:

```bash
python3 --version
```

### 3. Install MemRunner

From inside the project folder, run:

```bash
pip install -e .
```

If that does not work on your system, try:

```bash
python -m pip install -e .
```

or:

```bash
python3 -m pip install -e .
```

## Starting the Dashboard

Run:

```bash
memrunner ui
```

Then open the local dashboard shown in your terminal. It will usually be something like:

```text
http://127.0.0.1:8000
```

The dashboard is the recommended way to use MemRunner.

## Dashboard Setup

In the dashboard, fill in the required settings:

* Email
* Password
* Course ID or course home link
* Prompt/source label
* Answer/target label
* Database path
* Headless mode preference
* Mute audio preference
* Action delay
* Idle timeout

Then click **Save Settings**.

## Course ID or Course Link

MemRunner accepts either a raw course ID or a full Memrise Community Course link.

You can enter a raw ID like:

```text
1234567
```

Or paste a full course home link like:

```text
https://community-courses.memrise.com/community/course/1234567/course-name/
```

You can also paste a mode link like:

```text
https://community-courses.memrise.com/aprender/learn?course_id=1234567
```

MemRunner will automatically extract the course ID.

## Vocabulary Setup

MemRunner uses a local vocabulary database. You can import vocabulary in two main ways.

### Option 1: Import aligned TXT files

Use this if you have two text files where each line matches the same line in the other file.

Example:

```text
spanish.txt line 1 = english.txt line 1
spanish.txt line 2 = english.txt line 2
spanish.txt line 3 = english.txt line 3
```

In the dashboard, use the aligned TXT import section and select both files.

### Option 2: Import CSV

You can also import vocabulary from a CSV file.

A simple CSV should include prompt and answer columns, such as:

```csv
prompt,answer,prompt_lang,answer_lang
hola,hello,Spanish,English
gracias,thank you,Spanish,English
```

You can also export your saved vocabulary back to CSV from the dashboard.

## Running Practice Modes

After saving settings and importing vocabulary, use the dashboard buttons:

* **Start Learn**
* **Start Classic Review**
* **Start Speed Review**
* **Stop Current Run**

For speed review, you can also choose the number of worker windows.

## Modes

### Learn Mode

Learn mode opens the course learning session, answers known questions, moves through presentation slides, and can save newly discovered vocabulary pairs.

### Classic Review Mode

Classic review mode answers standard review questions using the vocabulary database.

### Speed Review Mode

Speed review mode answers speed review prompts quickly. It can optionally run multiple browser windows for faster review sessions.

## Logs

The dashboard includes a logs area showing what MemRunner is doing, including:

* Current mode
* Browser startup
* Login progress
* Prompts detected
* Answers selected
* Newly learned vocabulary
* Errors or restarts

Use **Clear Logs** if you want to reset the display.

## Optional Command-Line Usage

The dashboard is recommended, but MemRunner also supports command-line usage.

Check status:

```bash
memrunner status
```

Import CSV:

```bash
memrunner import-csv data/sample_spanish_english.csv
```

Import aligned TXT files:

```bash
memrunner import-txt data/spanish.txt data/english.txt --prompt-lang Spanish --answer-lang English
```

Run learn mode:

```bash
memrunner learn
```

Run review mode:

```bash
memrunner review
```

Run speed review:

```bash
memrunner speed --workers 1
```

Open dashboard:

```bash
memrunner ui
```

## Optional `.env` Setup

Most users do not need to edit `.env` manually. The dashboard can save settings for you.

Advanced users may create a `.env` file using `.env.example` as a template:

```env
MEMRISE_EMAIL=your_email@example.com
MEMRISE_PASSWORD=your_password
MEMRISE_COURSE_ID=1234567
```

Dashboard settings are the recommended method.

## Local Data

MemRunner stores local settings and vocabulary on your own computer.

Typical local files may include:

```text
.memrunner/settings.json
.memrunner/memrunner.sqlite3
```

Do not commit personal settings, passwords, or private vocabulary files to GitHub.

## Troubleshooting

### `memrunner` command not found

Try:

```bash
python -m memrunner ui
```

or reinstall:

```bash
pip install -e .
```

### Browser does not open

Make sure Chrome is installed.

Also make sure Selenium and the project requirements installed correctly:

```bash
pip install -r requirements.txt
```

### Login fails

Check that your email and password are correct in the dashboard settings.

Also make sure you are using a Memrise Community Courses account and the correct course link or course ID.

### Course ID not found

Paste the full course home link into the dashboard instead of manually typing the course ID.

Example:

```text
https://community-courses.memrise.com/community/course/1234567/course-name/
```

### Vocabulary answers are not matching

Check that your imported vocabulary has the correct prompt and answer direction.

For example, if the course asks for Spanish and expects English, your database should contain:

```text
Prompt: Spanish
Answer: English
```

If the course asks for English and expects Spanish, reverse the direction or import both directions.

### Automation gets stuck

Memrise page layouts may change. Try stopping the run, refreshing the dashboard, and starting again.

If a specific button or prompt stops working consistently, the site selectors may need to be updated.

## Recommended GitHub Files

A public MemRunner repository should include:

```text
memrunner/
data/
.github/
README.md
LICENSE
requirements.txt
pyproject.toml
.env.example
.gitignore
```

Do not include:

```text
.env
.memrunner/settings.json
private vocabulary files
personal login information
```

## Project Status

MemRunner is currently an alpha local automation tool. It is usable, but browser automation can be fragile when websites change their layout.

Planned improvements include:

* Secure password storage through the operating system keychain
* More robust selector handling
* Better course/language detection
* Packaged Windows/macOS/Linux downloads
* Improved dashboard styling
* In-dashboard vocabulary editor
* Safer session controls
* Better error messages for non-technical users

## License

This project is released under the license included in the repository.

## Disclaimer

MemRunner is an independent local automation project. It is not affiliated with Memrise. Users are responsible for following all applicable terms, rules, and policies of any website or service they use with this tool.
