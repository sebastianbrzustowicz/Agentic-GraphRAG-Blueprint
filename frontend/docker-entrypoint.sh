#!/bin/sh
set -eu

if [ -z "${BACKEND_URL:-}" ]; then
    echo "ERROR: BACKEND_URL environment variable is required" >&2
    exit 1
fi

envsubst '${BACKEND_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

exec "$@"
