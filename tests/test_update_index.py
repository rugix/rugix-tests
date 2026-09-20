"""Exercise manual and automatic slot index management for system updates."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from rugix_testkit import RugixCtrl, VMHandle

from conftest import assert_boot, install_and_reboot
from harness import BakeryBuilder

SOURCE_INDEX_FILE = (
    "/run/rugix/mounts/data/rugix/slots/system-a/casync-64_sha512-256.rugix-block-index"
)
TARGET_INDEX_FILE = (
    "/run/rugix/mounts/data/rugix/slots/system-b/casync-64_sha512-256.rugix-block-index"
)


@pytest.fixture(params=[("system-a",), ("boot-a", "system-a")], ids=["single", "multi"])
def index_slots(request: pytest.FixtureRequest) -> tuple[str, ...]:
    return request.param


@pytest.mark.slow
def test_update_index(
    amd64_vm: VMHandle,
    rugix: RugixCtrl,
    bakery: BakeryBuilder,
    index_slots: tuple[str, ...],
    bundle_url: Callable[[Path], str],
) -> None:
    for slot in index_slots:
        amd64_vm.run(
            ["rugix-ctrl", "slots", "create-index", slot, "casync-64", "sha512-256"],
            hide=True,
        )
    amd64_vm.run(["test", "-e", SOURCE_INDEX_FILE], hide=True)

    assert_boot(rugix, default="a", active="a")

    install_and_reboot(rugix, bundle_url(bakery.bake_bundle("customized-amd64")))

    assert_boot(rugix, default="a", active="b")
    rugix.system_commit()
    assert_boot(rugix, default="b", active="b")


@pytest.mark.slow
def test_automatic_update_indices(
    amd64_vm: VMHandle,
    rugix: RugixCtrl,
    bakery: BakeryBuilder,
    bundle_url: Callable[[Path], str],
) -> None:
    """Create source indices and retain target indices during a full update."""
    amd64_vm.run(
        [
            "sh",
            "-c",
            "printf '%s\\n' 'automatic-delta-updates = true' > /etc/rugix/ctrl.toml",
        ],
        hide=True,
    )
    amd64_vm.run(["test", "!", "-e", SOURCE_INDEX_FILE], hide=True)
    amd64_vm.run(["test", "!", "-e", TARGET_INDEX_FILE], hide=True)

    assert_boot(rugix, default="a", active="a")
    install_and_reboot(rugix, bundle_url(bakery.bake_bundle("customized-amd64")))

    amd64_vm.run(["test", "-e", SOURCE_INDEX_FILE], hide=True)
    amd64_vm.run(["test", "-e", TARGET_INDEX_FILE], hide=True)
    assert_boot(rugix, default="a", active="b")
    rugix.system_commit()
    assert_boot(rugix, default="b", active="b")
