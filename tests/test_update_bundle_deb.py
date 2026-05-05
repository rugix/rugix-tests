"""Port of ``tests/tests/test-update-bundle-deb.toml`` and ``-deb-gnu.toml``.

Each variant boots a system whose rugix-ctrl was installed via deb packages
(rugix-ctrl-musl / rugix-ctrl-gnu). Verifies the dpkg install marker, then
runs one A/B install + commit cycle.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from conftest import assert_boot, install_and_reboot
from harness import BakeryBuilder
from rugix_testkit import RugixCtrl, VMHandle


@pytest.fixture(
    params=[
        ("customized-amd64-deb-musl", "rugix-ctrl-musl"),
        ("customized-amd64-deb-gnu", "rugix-ctrl-gnu"),
    ],
    ids=["musl", "gnu"],
)
def deb_variant(request: pytest.FixtureRequest) -> tuple[str, str]:
    return request.param


@pytest.fixture
def boot_system(deb_variant: tuple[str, str]) -> str:
    return deb_variant[0]


@pytest.mark.slow
def test_update_bundle_deb(
    amd64_vm: VMHandle,
    rugix: RugixCtrl,
    bakery: BakeryBuilder,
    deb_variant: tuple[str, str],
    bundle_url: Callable[[Path], str],
) -> None:
    system, package_name = deb_variant

    amd64_vm.run(["dpkg", "-s", package_name], hide=True)
    assert_boot(rugix, default="a", active="a")

    install_and_reboot(rugix, bundle_url(bakery.bake_bundle(system)))

    assert_boot(rugix, default="a", active="b")
    rugix.system_commit()
    assert_boot(rugix, default="b", active="b")
