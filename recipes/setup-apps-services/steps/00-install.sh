#!/bin/bash

set -euo pipefail

install -D -m 644 "${RECIPE_DIR}/files/rugix-app-sync.service" -t /usr/lib/systemd/system/
install -D -m 644 "${RECIPE_DIR}/files/rugix-app-recover.service" -t /usr/lib/systemd/system/
install -D -m 644 "${RECIPE_DIR}/files/rugix-app-gc.service" -t /usr/lib/systemd/system/
install -D -m 644 "${RECIPE_DIR}/files/rugix-app-gc.timer" -t /usr/lib/systemd/system/

systemctl enable rugix-app-sync
systemctl enable rugix-app-recover
systemctl enable rugix-app-gc.timer
