#!/usr/bin/env bash
set -euo pipefail
tests_dir=$(cd "$(dirname "$0")" && pwd)
cd "$tests_dir"
exec node node_modules/@playwright/test/cli.js test --config playwright.config.js --workers=1 "$@"
