#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo_dir"
image="lnbits/lnbits:${LNBITS_VERSION:-v1.6.1}"
work=$(mktemp -d)
network="allowance-install-$$"
container="allowance-install-postgres-$$"
cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
  rm -rf "$work"
}
trap cleanup EXIT
python3 scripts/build_release.py --repository BenGWeeks/allowance --output "$work/candidate"
curl --fail --location --retry 3 --output "$work/previous.zip" \
  https://github.com/BenGWeeks/allowance/releases/download/v1.0.6/allowance-1.0.6.zip
printf '%s  %s\n' 538620a14642d6200a8ddc000a5fa8557e9453bda6728c612b452a4d721fe4ce \
  "$work/previous.zip" | sha256sum --check
candidate=$(basename "$work"/candidate/*.zip)
for mode in fresh upgrade warm_upgrade; do
  docker run --rm --network none \
    -e LNBITS_DATA_FOLDER=/tmp/allowance-install-test \
    -e LNBITS_BACKEND_WALLET_CLASS=FakeWallet -e LOGURU_LEVEL=ERROR \
    -v "$work:/artifacts:ro" -v "$repo_dir/tests:/tests:ro" \
    "$image" /app/.venv/bin/python /tests/check_release_install.py \
    "$mode" "/artifacts/candidate/$candidate" /artifacts/previous.zip
done
docker network create --internal "$network" >/dev/null
docker run -d --name "$container" --network "$network" \
  --network-alias allowance-install-postgres \
  -e POSTGRES_USER=allowance_install -e POSTGRES_HOST_AUTH_METHOD=trust \
  postgres:15 -c timezone=America/New_York >/dev/null
for attempt in {1..30}; do
  if docker exec "$container" pg_isready -h 127.0.0.1 -U allowance_install >/dev/null; then break; fi
  sleep 1
done
docker exec "$container" pg_isready -h 127.0.0.1 -U allowance_install
for mode in fresh upgrade warm_upgrade; do
  docker exec "$container" createdb -U allowance_install "allowance_$mode"
  docker run --rm --network "$network" \
    -e LNBITS_DATABASE_URL="postgres://allowance_install@allowance-install-postgres:5432/allowance_$mode" \
    -e LNBITS_DATA_FOLDER=/tmp/allowance-install-test \
    -e LNBITS_BACKEND_WALLET_CLASS=FakeWallet -e LOGURU_LEVEL=ERROR \
    -v "$work:/artifacts:ro" -v "$repo_dir/tests:/tests:ro" \
    "$image" /app/.venv/bin/python /tests/check_release_install.py \
    "$mode" "/artifacts/candidate/$candidate" /artifacts/previous.zip
done
