#!/usr/bin/env python
"""Django's command-line utility for this website."""

import os
import sys


def main() -> None:
    """Run a Django management command."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django is unavailable. Start the project with Docker using the README instructions."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
