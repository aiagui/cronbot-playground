# cronbot-playground

Sandbox repository for Cronbot autonomous software engineering.

## Scheduled-job configuration validator

`jobconfig.py` validates JSON configuration before scheduled jobs are installed or
run. It has no third-party dependencies and reports every schema error it finds in
a single pass.

```json
{
  "version": 1,
  "jobs": [
    {
      "name": "hourly-report",
      "schedule": "0 * * * *",
      "command": ["python", "report.py", "--quiet"],
      "enabled": true
    }
  ]
}
```

Each schedule uses five numeric cron fields: minute, hour, day of month, month,
and day of week. Wildcards, comma-separated lists, ranges, and steps are supported.
Commands are arrays so argument boundaries remain explicit. Job names must be
unique. Unknown fields are rejected to catch misspellings.

Validate a file (or use `-` for standard input):

```sh
python jobconfig.py jobs.json
```

Exit status is `0` for valid input, `1` for schema errors, and `2` when JSON cannot
be read or decoded.

Run the tests with:

```sh
python -m unittest discover -s tests -v
```
