#!/usr/bin/env bash

set -euo pipefail

export RUGIX_BAKERY_IMAGE=${1:-"ghcr.io/rugix/rugix-bakery:dev"}
export RUGIX_DEV=true

rm -rf build
rm -rf .rugix

podman pull docker-daemon:"${RUGIX_BAKERY_IMAGE}"

./run-bakery bake bundle customized-arm64-deb-musl --disable-compression
./run-bakery bake bundle customized-arm64-deb-gnu --disable-compression
./run-bakery test test-update-bundle-deb-gnu
./run-bakery test test-update-bundle-deb
