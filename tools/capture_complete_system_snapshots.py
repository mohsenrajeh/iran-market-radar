"""Compatibility wrapper for the canonical screenshot audit.

The canonical script authenticates through the real HttpOnly owner session and
writes only under output/playwright. It never injects a mock browser token.
"""
from tools.capture_screenshots import main


if __name__ == "__main__":
    main()
