import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from jobconfig import main, validate_config


def valid_config():
    return {
        "version": 1,
        "jobs": [
            {
                "name": "hourly-report",
                "schedule": "0 * * * *",
                "command": ["python", "report.py", "--quiet"],
                "enabled": True,
            }
        ],
    }


class ValidateConfigTests(unittest.TestCase):
    def test_accepts_valid_configuration(self):
        self.assertEqual(validate_config(valid_config()), [])

    def test_accepts_empty_jobs_array(self):
        self.assertEqual(validate_config({"version": 1, "jobs": []}), [])

    def test_accepts_cron_lists_ranges_and_steps(self):
        config = valid_config()
        config["jobs"][0]["schedule"] = "*/15 8-17 * 1,6,12 1-5"
        self.assertEqual(validate_config(config), [])

    def test_rejects_non_object_root(self):
        self.assertEqual(validate_config([]), ["$: must be an object"])

    def test_reports_multiple_schema_errors(self):
        config = {"version": True, "jobs": "daily", "typo": 1}
        errors = validate_config(config)
        self.assertEqual(len(errors), 3)
        self.assertIn("$.typo: unknown field", errors)
        self.assertIn("$.version: must be the integer 1", errors)
        self.assertIn("$.jobs: must be an array", errors)

    def test_rejects_unknown_job_field(self):
        config = valid_config()
        config["jobs"][0]["timeout"] = 30
        self.assertEqual(validate_config(config), ["$.jobs[0].timeout: unknown field"])

    def test_rejects_duplicate_names(self):
        config = valid_config()
        config["jobs"].append(dict(config["jobs"][0]))
        self.assertIn("$.jobs[1].name: duplicate job name 'hourly-report'", validate_config(config))

    def test_rejects_invalid_name_and_command(self):
        config = valid_config()
        config["jobs"][0]["name"] = "bad name"
        config["jobs"][0]["command"] = ["python", ""]
        errors = validate_config(config)
        self.assertEqual(len(errors), 2)
        self.assertTrue(errors[0].startswith("$.jobs[0].name:"))
        self.assertTrue(errors[1].startswith("$.jobs[0].command:"))

    def test_rejects_cron_with_wrong_field_count(self):
        config = valid_config()
        config["jobs"][0]["schedule"] = "0 12 * *"
        self.assertIn("exactly five cron fields", validate_config(config)[0])

    def test_rejects_out_of_range_cron_value(self):
        config = valid_config()
        config["jobs"][0]["schedule"] = "60 12 * * *"
        self.assertIn("minute must be between 0 and 59", validate_config(config)[0])

    def test_rejects_descending_range_and_zero_step(self):
        config = valid_config()
        config["jobs"][0]["schedule"] = "0 18-8 * * *"
        self.assertIn("descending range", validate_config(config)[0])
        config["jobs"][0]["schedule"] = "*/0 * * * *"
        self.assertIn("invalid step", validate_config(config)[0])


class CliTests(unittest.TestCase):
    def run_cli(self, argv, stdin=None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(argv, stdin=stdin)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_valid_file_exits_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.json"
            path.write_text(json.dumps(valid_config()), encoding="utf-8")
            code, stdout, stderr = self.run_cli([str(path)])
        self.assertEqual(code, 0)
        self.assertEqual(stdout, "configuration is valid\n")
        self.assertEqual(stderr, "")

    def test_invalid_schema_exits_one_and_uses_stderr(self):
        code, stdout, stderr = self.run_cli(["-"], io.StringIO('{"version": 1, "jobs": {}}'))
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("$.jobs: must be an array", stderr)

    def test_malformed_json_exits_two(self):
        code, stdout, stderr = self.run_cli(["-"], io.StringIO("{"))
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("error: could not read JSON", stderr)


if __name__ == "__main__":
    unittest.main()
