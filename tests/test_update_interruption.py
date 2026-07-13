"""A forced reboot during streaming installation must not select an incomplete target."""

from __future__ import annotations

import shlex
from collections.abc import Callable
from pathlib import Path

import pytest

from conftest import assert_boot, install_and_reboot
from harness import BakeryBuilder
from rugix_testkit import RugixCtrl, VMHandle


@pytest.mark.slow
def test_forced_reboot_during_update_is_resumable(
    amd64_vm: VMHandle,
    rugix: RugixCtrl,
    bakery: BakeryBuilder,
    bundle_url: Callable[[Path], str],
) -> None:
    bundle = bundle_url(bakery.bake_bundle("customized-amd64"))
    assert_boot(rugix, default="a", active="a")

    # Rate limiting keeps the producer alive while Rugix is decoding the inactive
    # target. The explicit liveness check prevents a completed update from being
    # mistaken for an interrupted one.
    command = f"""
set -eu
(curl --fail --silent --show-error --limit-rate 1m {shlex.quote(bundle)} |
  rugix-ctrl update install --reboot set \
    --insecure-skip-bundle-verification -) >/tmp/interrupted-update.log 2>&1 &
installer=$!
sleep 8
kill -0 "$installer"
reboot -f
"""
    try:
        amd64_vm.run(["sh", "-c", command], check=False, hide=True, timeout=30)
    except Exception:
        # The forced reboot intentionally tears down the SSH transport.
        pass
    amd64_vm.wait_for_reboot(timeout=600)

    assert_boot(rugix, default="a", active="a")
    assert not amd64_vm.run(
        ["test", "-e", "/run/rugix/mounts/data/.rugix/deferred-reboot-spare"],
        check=False,
        hide=True,
    ).ok

    # Reinstalling overwrites the inactive destination and completes normally.
    install_and_reboot(rugix, bundle)
    assert_boot(rugix, default="a", active="b")
    rugix.system_commit()
    assert_boot(rugix, default="b", active="b")
