#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


SECRET_PATTERN = re.compile(r"^\$\{\{\s*secrets\.([A-Za-z_][A-Za-z0-9_]*)\s*\}\}$")
MAPPING_PATTERN = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_-]*):(?:\s*(?P<value>.*))?$")
SENSITIVE_KEY_PARTS = ("PASSWORD", "TOKEN", "SECRET")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run rental_car_alert locally using the env block from a GitHub "
            "Actions workflow job."
        )
    )
    parser.add_argument(
        "workflow",
        type=Path,
        help="Workflow file to read, for example .github/workflows/flores_airport_alert.yml.",
    )
    parser.add_argument(
        "--job",
        help="Workflow job id to use. Defaults to the only job in the workflow.",
    )
    parser.add_argument(
        "--list-jobs",
        action="store_true",
        help="List job ids found in the workflow and exit.",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Override RCA_HEADLESS=false so the browser is visible locally.",
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Disable email delivery by clearing RCA_SMTP_PASSWORD for this run.",
    )
    parser.add_argument(
        "--allow-missing-secrets",
        action="store_true",
        help="Do not fail when a workflow secret is not present locally.",
    )
    parser.add_argument(
        "--show-env",
        action="store_true",
        help="Print the resolved RCA_* environment before running.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve and print configuration without starting the monitor.",
    )
    args = parser.parse_args()

    workflow = args.workflow.resolve()
    jobs = list_jobs(workflow)
    if args.list_jobs:
        for job in jobs:
            print(job)
        return 0

    job = select_job(jobs, args.job, workflow)
    workflow_env = read_job_env(workflow, job)
    dotenv_values = load_dotenv_values(Path.cwd())
    env, missing_secrets = build_env(
        workflow_env=workflow_env,
        dotenv_values=dotenv_values,
        no_email=args.no_email,
    )

    if missing_secrets and not args.allow_missing_secrets:
        names = ", ".join(sorted(missing_secrets))
        print(
            f"Missing local values for workflow secrets: {names}. "
            "Export them or add them to .env, then retry. Use --no-email when "
            "you want to debug without SMTP secrets.",
            file=sys.stderr,
        )
        return 2

    if args.headful:
        env["RCA_HEADLESS"] = "false"
    if args.no_email:
        env["RCA_SMTP_PASSWORD"] = ""

    print(f"Workflow: {workflow}")
    print(f"Job: {job}")
    if args.show_env or args.dry_run:
        print_resolved_env(env, workflow_env.keys())

    if args.dry_run:
        return 0

    command = [sys.executable, "-m", "rental_car_alert"]
    print(f"Running: {' '.join(command)}")
    return subprocess.run(command, env=env, check=False).returncode


def list_jobs(workflow: Path) -> list[str]:
    lines = read_lines(workflow)
    jobs: list[str] = []
    in_jobs = False

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = indentation(line)
        if indent == 0:
            in_jobs = stripped == "jobs:"
            continue

        if in_jobs and indent == 2:
            match = MAPPING_PATTERN.match(stripped)
            if match and not match.group("value"):
                jobs.append(match.group("key"))

    return jobs


def select_job(jobs: list[str], requested_job: str | None, workflow: Path) -> str:
    if requested_job:
        if requested_job not in jobs:
            available = ", ".join(jobs) or "none"
            raise SystemExit(
                f"Job {requested_job!r} was not found in {workflow}. "
                f"Available jobs: {available}."
            )
        return requested_job

    if len(jobs) == 1:
        return jobs[0]

    available = ", ".join(jobs) or "none"
    raise SystemExit(
        f"{workflow} contains {len(jobs)} jobs. Pass --job. Available jobs: {available}."
    )


def read_job_env(workflow: Path, job: str) -> dict[str, str]:
    lines = read_lines(workflow)
    in_jobs = False
    in_job = False
    in_env = False
    env_indent = -1
    values: dict[str, str] = {}

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = indentation(line)
        if indent == 0:
            in_jobs = stripped == "jobs:"
            in_job = False
            in_env = False
            continue

        if in_jobs and indent == 2:
            match = MAPPING_PATTERN.match(stripped)
            in_job = bool(match and match.group("key") == job and not match.group("value"))
            in_env = False
            continue

        if not in_job:
            continue

        if indent == 4 and stripped == "env:":
            in_env = True
            env_indent = indent
            continue

        if in_env:
            if indent <= env_indent:
                in_env = False
                continue
            if indent == env_indent + 2:
                match = MAPPING_PATTERN.match(stripped)
                if match:
                    values[match.group("key")] = parse_scalar(match.group("value") or "")

    if not values:
        raise SystemExit(f"No env block found for job {job!r} in {workflow}.")
    return values


def build_env(
    workflow_env: dict[str, str],
    dotenv_values: dict[str, str],
    no_email: bool,
) -> tuple[dict[str, str], set[str]]:
    env = os.environ.copy()
    missing_secrets: set[str] = set()

    for key, value in workflow_env.items():
        secret_match = SECRET_PATTERN.match(value)
        if secret_match is None:
            env[key] = value
            continue

        secret_name = secret_match.group(1)
        secret_value = os.environ.get(secret_name, dotenv_values.get(secret_name))
        if secret_value is None:
            if no_email and (key.startswith("RCA_EMAIL_") or key.startswith("RCA_SMTP_")):
                env[key] = ""
                continue
            missing_secrets.add(secret_name)
            continue

        env[key] = secret_value

    return env, missing_secrets


def load_dotenv_values(start_path: Path) -> dict[str, str]:
    for base_path in [start_path, *start_path.parents]:
        env_path = base_path / ".env"
        if env_path.exists():
            return parse_dotenv(env_path)
    return {}


def parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = parse_scalar(value.strip())
    return values


def parse_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def print_resolved_env(env: dict[str, str], keys: list[str] | set[str]) -> None:
    print("Resolved workflow env:")
    for key in sorted(keys):
        value = env.get(key, "")
        print(f"  {key}={redact(key, value)}")


def redact(key: str, value: str) -> str:
    if any(part in key.upper() for part in SENSITIVE_KEY_PARTS):
        return "<set>" if value else "<empty>"
    return value


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        raise SystemExit(f"Workflow file not found: {path}") from None


def indentation(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


if __name__ == "__main__":
    raise SystemExit(main())
