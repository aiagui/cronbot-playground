"""Validate JSON configuration for scheduled jobs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, TextIO


NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,62}[A-Za-z0-9])?")
CRON_FIELDS = (
    ("minute", 0, 59),
    ("hour", 0, 23),
    ("day of month", 1, 31),
    ("month", 1, 12),
    ("day of week", 0, 7),
)
ROOT_FIELDS = {"version", "jobs"}
JOB_FIELDS = {"name", "schedule", "command", "enabled"}


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_cron_part(part: str, minimum: int, maximum: int) -> str | None:
    base, separator, step_text = part.partition("/")
    if separator:
        if "/" in step_text or not step_text.isdigit() or int(step_text) < 1:
            return "has an invalid step"

    if base == "*":
        return None

    start_text, separator, end_text = base.partition("-")
    values = (start_text, end_text) if separator else (start_text,)
    if any(not value.isdigit() for value in values):
        return "must use numbers, '*', ranges, lists, or steps"

    numbers = tuple(int(value) for value in values)
    if any(number < minimum or number > maximum for number in numbers):
        return f"must be between {minimum} and {maximum}"
    if len(numbers) == 2 and numbers[0] > numbers[1]:
        return "has a descending range"
    return None


def _validate_schedule(schedule: str) -> str | None:
    fields = schedule.split()
    if len(fields) != len(CRON_FIELDS):
        return "must contain exactly five cron fields"

    for value, (label, minimum, maximum) in zip(fields, CRON_FIELDS):
        for part in value.split(","):
            if not part:
                return f"has an empty item in the {label} field"
            problem = _validate_cron_part(part, minimum, maximum)
            if problem:
                return f"{label} {problem}"
    return None


def validate_config(config: Any) -> list[str]:
    """Return all validation errors found in a decoded JSON value."""
    if not isinstance(config, dict):
        return ["$: must be an object"]

    errors: list[str] = []
    for field in sorted(set(config) - ROOT_FIELDS):
        errors.append(f"$.{field}: unknown field")

    version = config.get("version")
    if not _is_integer(version) or version != 1:
        errors.append("$.version: must be the integer 1")

    jobs = config.get("jobs")
    if not isinstance(jobs, list):
        errors.append("$.jobs: must be an array")
        return errors

    names: set[str] = set()
    for index, job in enumerate(jobs):
        path = f"$.jobs[{index}]"
        if not isinstance(job, dict):
            errors.append(f"{path}: must be an object")
            continue

        for field in sorted(set(job) - JOB_FIELDS):
            errors.append(f"{path}.{field}: unknown field")

        name = job.get("name")
        if not isinstance(name, str) or not NAME.fullmatch(name):
            errors.append(
                f"{path}.name: must be 1-64 characters using letters, numbers, '.', '_' or '-'"
            )
        elif name in names:
            errors.append(f"{path}.name: duplicate job name {name!r}")
        else:
            names.add(name)

        schedule = job.get("schedule")
        if not isinstance(schedule, str):
            errors.append(f"{path}.schedule: must be a string")
        else:
            problem = _validate_schedule(schedule)
            if problem:
                errors.append(f"{path}.schedule: {problem}")

        command = job.get("command")
        if (
            not isinstance(command, list)
            or not command
            or any(not isinstance(argument, str) or not argument for argument in command)
        ):
            errors.append(f"{path}.command: must be a non-empty array of non-empty strings")

        if "enabled" in job and not isinstance(job["enabled"], bool):
            errors.append(f"{path}.enabled: must be a boolean")

    return errors


def _load_json(source: str, stdin: TextIO) -> Any:
    if source == "-":
        return json.load(stdin)
    with Path(source).open(encoding="utf-8") as stream:
        return json.load(stream)


def main(argv: list[str] | None = None, *, stdin: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jobconfig",
        description="Validate a scheduled-job JSON configuration.",
    )
    parser.add_argument("file", help="JSON file to validate, or '-' to read standard input")
    args = parser.parse_args(argv)

    try:
        config = _load_json(args.file, stdin or sys.stdin)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: could not read JSON: {exc}", file=sys.stderr)
        return 2

    errors = validate_config(config)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("configuration is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
