#!/usr/bin/env python3
"""Generate CLI help snapshots for all stable scripts."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = Path(__file__).resolve().parent
GENERATED_DIR = DOCS_DIR / "generated"

SCRIPTS = [
    ("junos_ping.py", "junos_ping"),
    ("jtac_collector.py", "jtac_collector"),
    ("junos_print_facts.py", "junos_print_facts"),
    ("junos_version.py", "junos_version"),
]

STATIC_FALLBACKS = {
    "junos_version": "This prototype currently accepts no CLI arguments beyond the defaults.",
}


def capture_help(script: str, name: str) -> str:
    script_path = ROOT / script
    cmd = ["uv", "run", "--script", str(script_path), "--help"]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.rstrip()
    except subprocess.CalledProcessError:
        fallback = STATIC_FALLBACKS.get(name)
        if fallback is None:
            raise
        return fallback


def main() -> None:
    GENERATED_DIR.mkdir(exist_ok=True)
    for script, name in SCRIPTS:
        help_text = capture_help(script, name)
        target = GENERATED_DIR / f"{name}_help.md"
        target.write_text(
            f"# {script}\n\n```text\n{help_text}\n```\n",
            encoding="utf-8",
        )
        print(f"Wrote {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
