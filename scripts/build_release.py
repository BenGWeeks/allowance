"""Build a versioned LNbits archive and its explicit-release manifest."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

REQUIRED = {
    "__init__.py",
    "config.json",
    "crud.py",
    "migrations.py",
    "models.py",
    "safe_http.py",
    "schedule.py",
    "tasks.py",
    "views.py",
    "views_api.py",
    "templates/allowance/index.html",
    "static/js/allowance.js",
    "static/image/allowance.png",
    "LICENSE",
    "README.md",
}
ALLOWED_ROOTS = {
    *(name for name in REQUIRED if "/" not in name),
    "templates",
    "static",
    "manifest.json",
    "description.md",
    "toc.md",
    "pyproject.toml",
}


def build_release(ref: str, repository: str, output: Path, tag: str | None = None):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Expected an owner/repository GitHub name")
    commit = subprocess.check_output(
        ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], text=True
    ).strip()
    config = json.loads(
        subprocess.check_output(["git", "show", f"{commit}:config.json"])
    )
    version = config["version"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("config.json must contain a stable semantic version")
    if tag is not None and tag != f"v{version}":
        raise ValueError("Release tag must match config.json version")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"allowance-{version}.zip"
    subprocess.run(
        [
            "git",
            "archive",
            "--format=zip",
            "--prefix=allowance/",
            f"--output={archive.resolve()}",
            commit,
        ],
        check=True,
    )
    with ZipFile(archive) as package:
        files = {
            str(PurePosixPath(name).relative_to("allowance"))
            for name in package.namelist()
            if not name.endswith("/")
        }
        unexpected = {
            name for name in files if PurePosixPath(name).parts[0] not in ALLOWED_ROOTS
        }
        if REQUIRED - files or unexpected:
            raise ValueError(
                f"Invalid archive: missing={REQUIRED - files}, extra={unexpected}"
            )
        if any(
            part.startswith(".") or part in {"__pycache__", "node_modules"}
            for name in files
            for part in PurePosixPath(name).parts
        ):
            raise ValueError("Development or hidden files in release archive")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n")
    repo_url = f"https://github.com/{repository}"
    raw_url = f"https://raw.githubusercontent.com/{repository}/v{version}"
    entry = {
        "id": "allowance",
        "repo": repo_url,
        "name": config["name"],
        "version": version,
        "min_lnbits_version": config["min_lnbits_version"],
        "short_description": config["short_description"],
        "icon": f"{raw_url}/static/image/allowance.png",
        "details_link": f"{raw_url}/config.json",
        "archive": f"{repo_url}/releases/download/v{version}/{archive.name}",
        "hash": digest,
    }
    (output / "release-manifest.json").write_text(
        json.dumps({"extensions": [entry]}, indent=2) + "\n"
    )
    print(f"Built {archive.name} from {commit}; SHA256 {digest}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tag")
    args = parser.parse_args()
    build_release(args.ref, args.repository, args.output, args.tag)
