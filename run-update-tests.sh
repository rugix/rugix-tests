#!/usr/bin/env bash

set -euo pipefail

rm -rf .rugix
rm -rf build

mkdir build
mkdir -p apps/build

export RUGIX_DEV=true

./run-bakery bake bundle customized-amd64
./run-bakery bake bundle customized-amd64-delta
./run-bakery bundler delta build/customized-amd64/system.rugixb build/customized-amd64-delta/system.rugixb build/delta.rugixb
./run-bakery bundler signatures sign build/customized-amd64/system.rugixb keys/signer.crt keys/signer.key build/customized-amd64-signed.rugixb

./run-bakery bundler apps pack docker-compose \
    --pull \
    --platform linux/amd64 \
    --app website \
    --include "apps/docker-compose-website/www" \
    "apps/docker-compose-website/docker-compose.yml" \
    "apps/build/docker-compose-website_amd64.rugixb"

echo "TEST: test-update-bundle"
./run-bakery test test-update-bundle
echo "TEST: test-update-bundle-signed"
./run-bakery test test-update-bundle-signed
echo "TEST: test-update-index"
./run-bakery test test-update-index
echo "TEST: test-update-index-http"
./run-bakery test test-update-index-http
echo "TEST: test-update-index-multi"
./run-bakery test test-update-index-multi
echo "TEST: test-update-static-delta"
./run-bakery test test-update-static-delta

./run-bakery bundler apps pack binary \
    --app hello-binary \
    --service "apps/binary-hello/hello-server.service" \
    "apps/binary-hello/hello-server" \
    "apps/build/binary-hello_amd64.rugixb"

./run-bakery bundler apps pack generic \
    --app hello-generic \
    "apps/generic-hello/orchestrator" \
    "apps/build/generic-hello_amd64.rugixb"

echo "TEST: test-apps-docker-compose"
./run-bakery test test-apps-docker-compose

echo "TEST: test-apps-binary"
./run-bakery test test-apps-binary

echo "TEST: test-apps-generic"
./run-bakery test test-apps-generic

./run-bakery bundler bundle bundles/script-bundle build/script-bundle.rugixb
echo "TEST: test-update-script"
./run-bakery test test-update-script

rm -f bundles/slots-bundle/payloads/test-dir.tar
tar -cvf bundles/slots-bundle/payloads/test-dir.tar -C bundles/slots-bundle/payloads test-file
./run-bakery bundler bundle bundles/slots-bundle build/slots-bundle.rugixb
echo "TEST: test-update-custom-slots"
./run-bakery test test-update-custom-slots
