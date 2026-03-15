#!/bin/sh
set -eu

# Pack the example Docker Compose app into an app bundle.
#
# Usage:
#   ./pack.sh [output.rugix]
#
# This bundles a static website served by Nginx. Docker images
# referenced in the compose file are automatically saved and included.

cargo run --target x86_64-unknown-linux-musl -p rugix-bundler -- \
    apps pack docker-compose \
    --pull \
    --platform linux/arm64 \
    --app website \
    --include "www" \
    "docker-compose.yml" \
    "app-bundle-arm64.rugixb"

cargo run --target x86_64-unknown-linux-musl -p rugix-bundler -- \
    apps pack docker-compose \
    --pull \
    --platform linux/amd64 \
    --app website \
    --include "www" \
    "docker-compose.yml" \
    "app-bundle-amd64.rugixb"
