#!/bin/sh
set -eu

# Pack the example Docker Compose app into an app bundle.
#
# Usage:
#   ./pack.sh [output.rugix]
#
# This bundles a static website served by Nginx. Docker images
# referenced in the compose file are automatically saved and included.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="${1:-$SCRIPT_DIR/app-bundle-arm64.rugixb}"

exec cargo run --target x86_64-unknown-linux-musl -p rugix-bundler -- \
    apps pack docker-compose \
    --pull \
    --platform linux/arm64 \
    --app website \
    --include "$SCRIPT_DIR/www" \
    "$SCRIPT_DIR/docker-compose.yml" \
    "$OUTPUT"
