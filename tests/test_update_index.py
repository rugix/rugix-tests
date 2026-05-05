"""Port of ``tests/tests/test-update-index.toml`` and ``-multi.toml``.

Both create slot indices via ``rugix-ctrl slots create-index`` before
installing the regular ``customized-amd64`` bundle. ``-multi`` exercises
indices on both ``boot-a`` and ``system-a``.
"""

from __future__ import annotations

import pytest

from conftest import assert_boot, install_and_reboot
from harness import BakeryBuilder
from rugix_testkit import RugixCtrl, VMHandle

INDEX_FILE = (
    "/run/rugix/mounts/data/rugix/slots/system-a/casync-64_sha512-256.rugix-block-index"
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
) -> None:
    for slot in index_slots:
        amd64_vm.run(
            ["rugix-ctrl", "slots", "create-index", slot, "casync-64", "sha512-256"],
            hide=True,
        )
    amd64_vm.run(["test", "-e", INDEX_FILE], hide=True)

    assert_boot(rugix, default="a", active="a")

    bundle = bakery.bake_bundle("customized-amd64")
    install_and_reboot(rugix, bundle)

    assert_boot(rugix, default="a", active="b")
    rugix.system_commit()
    assert_boot(rugix, default="b", active="b")
