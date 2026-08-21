#!/usr/bin/env bash

set -euo pipefail

# This test verifies reproducible layer archives and system ext4 filesystems
# across clean Bakery builds of the same immutable Debian snapshot.

rm -rf .rugix
RUGIX_DEV=true ./run-bakery bake image old-debian-snapshot --release-version 20250629165915 --source-date 2025-06-29T16:20:02Z
mv build/old-debian-snapshot/filesystems build/filesystems-old
rm -rf .rugix
rm -rf build/old-debian-snapshot/
RUGIX_DEV=true ./run-bakery bake image old-debian-snapshot --release-version 20250629165915 --source-date 2025-06-29T16:20:02Z
mv build/old-debian-snapshot/filesystems build/filesystems-new

for old_archive in build/filesystems-old/*.tar; do
    archive_name=$(basename "${old_archive}")
    cmp "${old_archive}" "build/filesystems-new/${archive_name}"
done
cmp build/filesystems-old/partition-4.img build/filesystems-new/partition-4.img
