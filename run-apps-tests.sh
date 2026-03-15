#!/usr/bin/env bash

set -euo pipefail

#rm -rf .rugix
rm -rf build
mkdir build

export RUGIX_DEV=true

# Build the system image with Docker support.
./run-bakery bake image customized-arm64-docker

# Build the Docker Compose app bundle.
rugix-bundler apps pack docker-compose \
    --app website \
    --include apps/docker-compose-example/www \
    apps/docker-compose-example/docker-compose.yml \
    build/apps-docker-compose.rugixb

echo "TEST: test-apps-docker-compose"
./run-bakery test test-apps-docker-compose
