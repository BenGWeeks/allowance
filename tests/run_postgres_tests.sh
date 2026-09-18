#!/usr/bin/env bash
# Disposable, isolated PostgreSQL regression environment; no host ports or volumes.
set -euo pipefail
repo_dir=$(cd "$(dirname "$0")/.." && pwd)
network="allowance-regression-$$"
container="allowance-postgres-$$"
cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker network create --internal "$network" >/dev/null
docker run -d --name "$container" --network "$network" \
  --network-alias allowance-postgres-test \
  -e POSTGRES_USER=allowance_tests -e POSTGRES_DB=allowance_tests \
  -e POSTGRES_HOST_AUTH_METHOD=trust postgres:15 -c timezone=America/New_York >/dev/null
for attempt in {1..30}; do
  if docker exec "$container" pg_isready -h 127.0.0.1 -U allowance_tests >/dev/null; then break; fi
  sleep 1
done
docker exec "$container" pg_isready -h 127.0.0.1 -U allowance_tests
docker run --rm --network "$network" \
  -e ALLOWANCE_POSTGRES_TEST=1 \
  -e LNBITS_DATABASE_URL=postgres://allowance_tests@allowance-postgres-test:5432/allowance_tests \
  -e LNBITS_DATA_FOLDER=/tmp/allowance-tests \
  -e LNBITS_BACKEND_WALLET_CLASS=FakeWallet -e LOGURU_LEVEL=ERROR \
  -v "$repo_dir:/app/lnbits/extensions/allowance:ro" \
  lnbits/lnbits:v1.6.1 \
  /app/.venv/bin/python /app/lnbits/extensions/allowance/tests/run_unit_tests.py
