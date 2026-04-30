#!/bin/bash
set -e

# build prefix
CHATGPT_ON_WECHAT_PREFIX=${CHATGPT_ON_WECHAT_PREFIX:-""}
# execution command line
CHATGPT_ON_WECHAT_EXEC=${CHATGPT_ON_WECHAT_EXEC:-""}

# CHATGPT_ON_WECHAT_PREFIX is empty, use /app
if [ "$CHATGPT_ON_WECHAT_PREFIX" == "" ] ; then
    CHATGPT_ON_WECHAT_PREFIX=/app
fi

if [ "$#" -gt 0 ]; then
    CHATGPT_ON_WECHAT_EXEC="$*"
fi

# CHATGPT_ON_WECHAT_EXEC is empty, use ‘python app.py’
if [ "$CHATGPT_ON_WECHAT_EXEC" == "" ] ; then
    CHATGPT_ON_WECHAT_EXEC="python app.py"
fi

if [ "${COW_PLATFORM_STRICT_STARTUP:-false}" = "true" ]; then
    python -m cow_platform.deployment.check \
        --require-all \
        --strict-secrets \
        --wait-seconds "${COW_PLATFORM_DEPENDENCY_WAIT_SECONDS:-90}"
fi

if [ -n "${COW_PLATFORM_DATABASE_URL:-}" ] && [ "${COW_PLATFORM_MIGRATE_ON_START:-true}" = "true" ]; then
    python -m cow_platform.db.migrate
fi

# fix ownership of mounted volumes then drop to non-root user
if [ "$(id -u)" = "0" ]; then
    mkdir -p /home/agent/cow
    chown agent:agent /home/agent/cow
    exec su agent -s /bin/bash -c "cd $CHATGPT_ON_WECHAT_PREFIX && $CHATGPT_ON_WECHAT_EXEC"
fi

# fallback: already running as agent
cd $CHATGPT_ON_WECHAT_PREFIX
$CHATGPT_ON_WECHAT_EXEC
