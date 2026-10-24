"""Set the local site name and generate a Django secret when needed."""

import argparse
import json
import os
from pathlib import Path

from django.core.management.utils import get_random_secret_key

ENV_FILE = Path(".env")
README_FILE = Path("README.md")
SITE_NAME_KEY = "WAGTAIL_SITE_NAME"
SECRET_KEY = "DJANGO_SECRET_KEY"
TITLE_START = "<!-- site-name:start -->"
TITLE_END = "<!-- site-name:end -->"


def get_env_value(lines: list[str], name: str) -> tuple[int, str] | None:
    """Find and decode a simple Docker Compose env-file value."""
    prefix = f"{name}="
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            value = line.partition("=")[2].strip()
            if value.startswith("'") and value.endswith("'"):
                value = value[1:-1].replace("\\'", "'")
            elif value.startswith('"') and value.endswith('"'):
                value = json.loads(value)
            return index, value
    return None


def update_readme_title(site_name: str) -> str:
    """Replace only the marked site-title block in the project README."""
    text = README_FILE.read_text(encoding="utf-8")
    if text.count(TITLE_START) != 1 or text.count(TITLE_END) != 1:
        raise SystemExit(
            "README.md must contain one site-name marker block to personalize."
        )

    before, remainder = text.split(TITLE_START, 1)
    _, after = remainder.split(TITLE_END, 1)
    return f"{before}{TITLE_START}\n# {site_name}\n{TITLE_END}{after}"


def main() -> None:
    """Personalize local site metadata without overwriting other settings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rotate",
        action="store_true",
        help="replace the existing local key instead of preserving it",
    )
    args = parser.parse_args()

    if not ENV_FILE.is_file():
        raise SystemExit(".env is missing. Run ./scripts/init.sh first.")
    if not README_FILE.is_file():
        raise SystemExit("README.md is missing from the repository root.")

    os.chmod(ENV_FILE, 0o600)
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    site_entry = get_env_value(lines, SITE_NAME_KEY)
    secret_entry = get_env_value(lines, SECRET_KEY)
    if site_entry is None:
        raise SystemExit(f"{SITE_NAME_KEY} entry is missing from .env.")
    if secret_entry is None:
        raise SystemExit(f"{SECRET_KEY} entry is missing from .env.")

    site_index, current_site_name = site_entry
    default_name = current_site_name or "New Website"
    entered_name = input(f"Site name [{default_name}]: ").strip()
    site_name = entered_name or default_name
    if not site_name.isprintable() or "<!--" in site_name or "-->" in site_name:
        raise SystemExit("Enter a printable, single-line site name.")

    updated_readme = update_readme_title(site_name)
    env_site_name = site_name.replace("'", "\\'")
    lines[site_index] = f"{SITE_NAME_KEY}='{env_site_name}'"

    secret_index, current_secret = secret_entry
    if current_secret and not args.rotate:
        secret_status = "DJANGO_SECRET_KEY is already set; leaving it unchanged."
    else:
        lines[secret_index] = f"{SECRET_KEY}={get_random_secret_key()}"
        secret_status = (
            "Rotated the local DJANGO_SECRET_KEY in .env."
            if args.rotate
            else "Generated a local DJANGO_SECRET_KEY in .env."
        )

    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(ENV_FILE, 0o600)
    README_FILE.write_text(updated_readme, encoding="utf-8")
    print(f"Configured site name: {site_name}.")
    print(secret_status)


if __name__ == "__main__":
    main()
