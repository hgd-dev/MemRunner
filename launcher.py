"""
MemRunner executable launcher.

This is used by PyInstaller to build a one-click app.
It launches the local dashboard automatically, instead of requiring
the user to type `memrunner ui`.
"""

import sys
from memrunner.cli import main


if __name__ == "__main__":
    sys.argv = ["memrunner", "ui"]
    main()
