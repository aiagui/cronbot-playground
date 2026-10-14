import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cronbot_toolkit.checksums import build_manifest


class BuildManifestTests(unittest.TestCase):
    def test_manifest_is_sorted_and_hashes_binary_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "nested").mkdir()
            (root / "z.txt").write_text("last", encoding="utf-8")
            content = b"\x00first\xff"
            (root / "nested" / "a.bin").write_bytes(content)

            manifest = build_manifest(root)

        self.assertEqual(
            [entry["path"] for entry in manifest], ["nested/a.bin", "z.txt"]
        )
        self.assertEqual(manifest[0]["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(manifest[0]["size"], len(content))

    def test_empty_directory_has_empty_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            self.assertEqual(build_manifest(temporary_directory), [])

    def test_missing_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing = Path(temporary_directory) / "missing"
            with self.assertRaisesRegex(ValueError, "not a directory"):
                build_manifest(missing)

    def test_file_as_root_is_rejected(self) -> None:
        with tempfile.NamedTemporaryFile() as file:
            with self.assertRaisesRegex(ValueError, "not a directory"):
                build_manifest(file.name)

    @unittest.skipUnless(hasattr(os, "symlink"), "symbolic links unavailable")
    def test_symbolic_link_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "target.txt").write_text("target", encoding="utf-8")
            (root / "link.txt").symlink_to(root / "target.txt")
            with self.assertRaisesRegex(ValueError, "symbolic links"):
                build_manifest(root)

    def test_cli_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "example.txt").write_text("example", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "cronbot_toolkit.checksums", str(root)],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(result.stdout)
        self.assertEqual(manifest[0]["path"], "example.txt")

    def test_cli_reports_invalid_root(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "cronbot_toolkit.checksums", "/does-not-exist"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("root is not a directory", result.stderr)


if __name__ == "__main__":
    unittest.main()
