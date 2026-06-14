"""Single execution path for running the CLI scripts as subprocesses.

The dashboard buttons and any other caller route through here instead of
building ``subprocess`` invocations inline, so the UI and the CLI scripts share
one code path. Command construction is split out as pure functions so it can be
unit-tested without spawning a process.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# jobsearch/services/pipeline_service.py → repo root is two levels up.
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"


@dataclass
class ScriptResult:
    returncode: int
    stdout: str
    stderr: str


def fetch_command() -> list[str]:
    return [sys.executable, str(SCRIPTS_DIR / "run_fetch.py")]


def auto_apply_command(
    limit: int,
    status: Optional[str] = None,
    min_priority: Optional[str] = None,
    job_id: Optional[int] = None,
    dry_run: bool = False,
) -> list[str]:
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "run_auto_apply.py"),
        "--limit",
        str(int(limit)),
    ]
    if status:
        cmd.extend(["--status", status])
    if min_priority:
        cmd.extend(["--min-priority", str(min_priority)])
    if job_id:
        cmd.extend(["--job-id", str(int(job_id))])
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def run_command(cmd: list[str]) -> ScriptResult:
    """Run a command from the repo root, capturing output."""
    completed = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    return ScriptResult(completed.returncode, completed.stdout, completed.stderr)


def run_fetch() -> ScriptResult:
    return run_command(fetch_command())


def run_auto_apply(
    limit: int,
    status: Optional[str] = None,
    min_priority: Optional[str] = None,
    job_id: Optional[int] = None,
    dry_run: bool = False,
) -> ScriptResult:
    return run_command(
        auto_apply_command(
            limit, status=status, min_priority=min_priority, job_id=job_id, dry_run=dry_run
        )
    )
