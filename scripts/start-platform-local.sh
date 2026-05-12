#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f ".env.docker" ]; then
  set -a
  # shellcheck disable=SC1091
  source ".env.docker"
  set +a
fi
DOCKER_WEB_PORT="${PLATFORM_WEB_PORT:-${WEB_PORT:-9899}}"

if [ -f ".env.local" ]; then
  set -a
  # shellcheck disable=SC1091
  source ".env.local"
  set +a
fi

LOCAL_WEB_PORT="${LOCAL_WEB_PORT:-9901}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
START_CHANNEL_RUNTIME="${START_CHANNEL_RUNTIME:-true}"
CHANNEL_RUNTIME_POLL_INTERVAL="${CHANNEL_RUNTIME_POLL_INTERVAL:-15}"
if [ "$LOCAL_WEB_PORT" = "$DOCKER_WEB_PORT" ]; then
  echo "LOCAL_WEB_PORT must differ from Docker WEB_PORT ($DOCKER_WEB_PORT) to avoid a port conflict." >&2
  exit 1
fi

export COW_PLATFORM_DATABASE_URL="postgresql://${PLATFORM_POSTGRES_USER:-cowplatform}:${PLATFORM_POSTGRES_PASSWORD:-prod-smoke-db-secret}@127.0.0.1:${PLATFORM_POSTGRES_PORT:-55432}/${PLATFORM_POSTGRES_DB:-cowplatform}"
export COW_PLATFORM_REDIS_URL="redis://127.0.0.1:${PLATFORM_REDIS_PORT:-56379}/0"
export COW_PLATFORM_QDRANT_URL="http://127.0.0.1:${PLATFORM_QDRANT_HTTP_PORT:-56333}"
export COW_PLATFORM_MINIO_ENDPOINT="http://127.0.0.1:${PLATFORM_MINIO_API_PORT:-59000}"
export COW_PLATFORM_MINIO_ACCESS_KEY="${PLATFORM_MINIO_ROOT_USER:-cowplatform-prod}"
export COW_PLATFORM_MINIO_SECRET_KEY="${PLATFORM_MINIO_ROOT_PASSWORD:-prod-smoke-minio-secret}"
export COW_PLATFORM_MINIO_BUCKET="${PLATFORM_MINIO_BUCKET:-coreagent}"
export COW_PLATFORM_ENV="dev"
export WEB_TENANT_AUTH="${WEB_TENANT_AUTH:-true}"
export WEB_PORT="$LOCAL_WEB_PORT"
export MODEL="${MODEL:-qwen3.6-plus}"
export AGENT_WORKSPACE="${AGENT_WORKSPACE:-$HOME/cow}"

CHANNEL_RUNTIME_PID=""
cleanup() {
  if [ -n "$CHANNEL_RUNTIME_PID" ] && kill -0 "$CHANNEL_RUNTIME_PID" 2>/dev/null; then
    kill "$CHANNEL_RUNTIME_PID" 2>/dev/null || true
    wait "$CHANNEL_RUNTIME_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

case "$START_CHANNEL_RUNTIME" in
  1|true|TRUE|yes|YES|on|ON)
    echo "Starting tenant channel runtime worker..."
    "$PYTHON_BIN" -m cow_platform.worker.channel_runtime --poll-interval "$CHANNEL_RUNTIME_POLL_INTERVAL" &
    CHANNEL_RUNTIME_PID="$!"
    ;;
esac

"$PYTHON_BIN" app.py
