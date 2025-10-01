#!/usr/bin/env python3
"""
Run CI code quality checks locally before committing.

This script automates the code quality checks that run in CI/CD:
- Black formatting
- Type checking with mypy
- Linting with ruff

Usage:
    python3 tests/run_ci_checks.py
    # or make it executable:
    chmod +x tests/run_ci_checks.py
    ./tests/run_ci_checks.py
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return True if successful."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(str(c) for c in cmd)}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)

    if result.returncode == 0:
        print(f"✅ {description} passed")
        return True
    else:
        print(f"❌ {description} failed")
        return False


def main():
    """Run all code quality checks."""
    print("Starting CI code quality checks...")

    checks = [
        (
            ["black", "--check", "."],
            "Black formatting check",
            "Run 'black .' to fix formatting issues",
        ),
        (
            ["mypy", "--ignore-missing-imports"]
            + [str(p) for p in Path(".").glob("*.py")],
            "Type checking with mypy",
            "Fix type errors reported above",
        ),
        (["ruff", "check", "."], "Linting with ruff", "Fix linting issues above"),
    ]

    results = []
    for cmd, description, fix_hint in checks:
        success = run_command(cmd, description)
        results.append((description, success, fix_hint))

    # Summary
    print(f"\n{'='*60}")
    print("Summary:")
    print(f"{'='*60}")

    all_passed = True
    for description, success, fix_hint in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {description}")
        if not success:
            print(f"  → {fix_hint}")
            all_passed = False

    if all_passed:
        print(f"\n{'='*60}")
        print("✅ All checks passed! Ready to commit.")
        print(f"{'='*60}")
        return 0
    else:
        print(f"\n{'='*60}")
        print("❌ Some checks failed. Fix the issues above before committing.")
        print(f"{'='*60}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
