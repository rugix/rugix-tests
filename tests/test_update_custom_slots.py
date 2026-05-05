"""Port of ``tests/tests/test-update-custom-slots.toml``.

Boots the ``customized-slots`` system, builds ``bundles/slots-bundle``
(tarring its payloads first), installs it, and verifies that the slot
payloads land at the expected paths under ``/run/rugix/state``.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from harness import BakeryBuilder
from rugix_testkit import RugixCtrl, VMHandle


@pytest.fixture
def boot_system() -> str:
    return "customized-slots"


@pytest.fixture(scope="session")
def slots_bundle(bakery: BakeryBuilder, project_dir: Path) -> Path:
    payloads = project_dir / "bundles" / "slots-bundle" / "payloads"
    test_tar = payloads / "test-dir.tar"
    test_tar.unlink(missing_ok=True)
    subprocess.run(
        ["tar", "-cf", str(test_tar), "-C", str(payloads), "test-file"],
        check=True,
    )
    output = project_dir / "build" / "slots-bundle.rugixb"
    if output.exists():
        output.unlink()
    bakery.bundler_bundle(project_dir / "bundles" / "slots-bundle", output)
    return output


@pytest.mark.slow
def test_update_custom_slots(
    amd64_vm: VMHandle,
    rugix: RugixCtrl,
    slots_bundle: Path,
    bundle_url: Callable[[Path], str],
) -> None:
    amd64_vm.run(["mkdir", "-p", "/run/rugix/state/app/custom-dir"], hide=True)

    for path in (
        "/run/rugix/state/test-file",
        "/run/rugix/state/app/custom-dir/test-file",
    ):
        res = amd64_vm.run(["test", "-e", path], check=False, hide=True)
        assert not res.ok, f"{path} must not exist before install"

    rugix.update_install(bundle_url(slots_bundle))

    amd64_vm.run(["test", "-e", "/run/rugix/state/test-file"], hide=True)
    amd64_vm.run(["test", "-e", "/run/rugix/state/app/custom-dir/test-file"], hide=True)
