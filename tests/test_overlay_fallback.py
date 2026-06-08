"""End-to-end tests for root overlay fallback handling."""

from __future__ import annotations

import pytest

from rugix_testkit import VMHandle


@pytest.fixture
def boot_system() -> str:
    return "customized-overlay-fallback"


def test_overlay_falls_back_to_in_memory(amd64_vm: VMHandle) -> None:
    amd64_vm.run(
        ["test", "-f", "/run/rugix/state/.rugix/overlay-fallback-error.log"],
        hide=True,
    )
    amd64_vm.run(["test", "-d", "/run/rugix/overlay/upper"], hide=True)

    log = amd64_vm.run(
        ["cat", "/run/rugix/state/.rugix/overlay-fallback-error.log"],
        hide=True,
    ).stdout
    assert "unable to setup system overlay mounts" in log

    info = amd64_vm.run_json(["rugix-ctrl", "system", "info", "--json"])
    assert info["state"]["status"] == "Error"
