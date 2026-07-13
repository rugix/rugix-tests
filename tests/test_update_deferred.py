"""Deferred update selection survives a shutdown boundary and targets the recorded group."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from conftest import assert_boot
from harness import BakeryBuilder
from rugix_testkit import RugixCtrl, VMHandle


@pytest.mark.slow
def test_deferred_update_reboots_into_recorded_group(
    amd64_vm: VMHandle,
    rugix: RugixCtrl,
    bakery: BakeryBuilder,
    bundle_url: Callable[[Path], str],
) -> None:
    bundle = bundle_url(bakery.bake_bundle("customized-amd64"))
    assert_boot(rugix, default="a", active="a")

    result = rugix.update_install(
        bundle,
        reboot="deferred",
        insecure=True,
        timeout=600,
        check=False,
    )
    assert result.ok, f"{result.stdout}\n{result.stderr}"
    assert_boot(rugix, default="a", active="a")

    marker = amd64_vm.run(
        ["cat", "/run/rugix/mounts/data/.rugix/deferred-reboot-spare"],
        hide=True,
    )
    assert json.loads(marker.stdout) == {"version": 1, "bootGroup": "b"}

    # Rugix processes the durable marker before userspace services start, selects
    # group B, clears the marker, and performs the second reboot automatically.
    amd64_vm.reboot(timeout=600)
    assert_boot(rugix, default="a", active="b")
    assert not amd64_vm.run(
        ["test", "-e", "/run/rugix/mounts/data/.rugix/deferred-reboot-spare"],
        check=False,
        hide=True,
    ).ok

    rugix.system_commit()
    assert_boot(rugix, default="b", active="b")
