"""
MemRunner executable launcher.

This file is used by PyInstaller/GitHub Actions to build a one-click app.
It starts the local dashboard so users do not need to run `memrunner ui`
from the command line.
"""

from memrunner.ui import main


if __name__ == "__main__":
    main(open_browser=True)
