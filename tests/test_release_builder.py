"""Check packaging failures using small, disposable Git repositories."""

import hashlib
import json
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

BUILDER = Path(__file__).resolve().parents[1] / "scripts/build_release.py"


class ReleaseBuilderTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.repo = Path(folder.name) / "repository"
        self.repo.mkdir()
        self.output = Path(folder.name) / "output"
        for name in runpy.run_path(str(BUILDER))["REQUIRED"]:
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n")
        (self.repo / "config.json").write_text(
            json.dumps(
                {
                    "version": "1.2.3",
                    "name": "Allowance",
                    "min_lnbits_version": "1.6.0",
                    "short_description": "Fixture",
                }
            )
        )
        (self.repo / ".gitattributes").write_text(
            "/.gitattributes export-ignore\n/private-fixture export-ignore\n"
        )
        (self.repo / "private-fixture").write_text("must not be packaged")
        self.git("init", "--quiet")
        self.commit()

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)

    def commit(self):
        self.git("add", ".")
        self.git(
            "-c",
            "user.name=Packaging test",
            "-c",
            "user.email=packaging@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "Fixture",
        )

    def build(self, tag="v1.2.3"):
        return subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--repository",
                "example/allowance",
                "--output",
                str(self.output),
                "--tag",
                tag,
            ],
            cwd=self.repo,
            capture_output=True,
            text=True,
        )

    def test_manifest_hash_and_archive_exclusions(self):
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stderr)
        archive = self.output / "allowance-1.2.3.zip"
        entry = json.loads((self.output / "release-manifest.json").read_text())[
            "extensions"
        ][0]
        self.assertEqual(
            entry["hash"], hashlib.sha256(archive.read_bytes()).hexdigest()
        )
        self.assertEqual(
            entry["archive"],
            "https://github.com/example/allowance/releases/download/v1.2.3/allowance-1.2.3.zip",
        )
        with ZipFile(archive) as package:
            self.assertNotIn("allowance/private-fixture", package.namelist())
            self.assertIn("allowance/README.md", package.namelist())

    def test_mismatched_tag_is_rejected(self):
        self.assertNotEqual(self.build("v9.9.9").returncode, 0)
        self.assertFalse(self.output.exists())

    def test_missing_runtime_file_is_rejected(self):
        (self.repo / "tasks.py").unlink()
        self.commit()
        self.assertNotEqual(self.build().returncode, 0)

    def test_unexpected_file_is_rejected(self):
        (self.repo / "credentials.txt").write_text("synthetic fixture")
        self.commit()
        self.assertNotEqual(self.build().returncode, 0)


if __name__ == "__main__":
    unittest.main()
