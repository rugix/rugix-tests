"""Port of ``tests/tests/test-update-static-delta.toml``.

Three-step update: first installs the regular ``customized-amd64`` bundle,
then installs a static delta to ``customized-amd64-delta``. A later regular
update computes the missing source index only when enabled.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from rugix_testkit import RugixCtrl, VMHandle

from conftest import assert_boot, install_and_reboot
from harness import BakeryBuilder, Bundler

SYSTEM_INDEX_FILE = (
    "/run/rugix/mounts/data/rugix/slots/{slot}/casync-64_sha512-256.rugix-block-index"
)


@pytest.fixture(scope="session")
def delta_bundle(bakery: BakeryBuilder, bundler: Bundler, project_dir: Path) -> Path:
    base = bakery.bake_bundle("customized-amd64")
    target = bakery.bake_bundle("customized-amd64-delta")
    output = project_dir / "build" / "delta.rugixb"
    bundler.delta(base, target, output)
    return output


@pytest.mark.slow
@pytest.mark.parametrize(
    "compute_missing_indices", [False, True], ids=["retain", "compute"]
)
def test_update_static_delta(
    amd64_vm: VMHandle,
    rugix: RugixCtrl,
    bakery: BakeryBuilder,
    delta_bundle: Path,
    bundle_url: Callable[[Path], str],
    compute_missing_indices: bool,
) -> None:
    """Static deltas leave no target index; later installs may compute it as a source."""
    base = bundle_url(bakery.bake_bundle("customized-amd64"))
    delta = bundle_url(delta_bundle)
    source_index = SYSTEM_INDEX_FILE.format(slot="system-b")
    target_index = SYSTEM_INDEX_FILE.format(slot="system-a")

    assert_boot(rugix, default="a", active="a")

    install_and_reboot(rugix, base)
    assert_boot(rugix, default="a", active="b")
    rugix.system_commit()
    assert_boot(rugix, default="b", active="b")

    amd64_vm.run(["test", "-e", source_index], hide=True)
    for update in (delta, base):
        if compute_missing_indices:
            amd64_vm.run(
                [
                    "sh",
                    "-c",
                    "printf '%s\\n' '[install]' 'auto-index = true' > /etc/rugix/ctrl.toml",
                ],
                hide=True,
            )
        install_and_reboot(rugix, update)
        if update == delta:
            amd64_vm.run(["test", "!", "-e", target_index], hide=True)
            assert_boot(rugix, default="b", active="a")
            rugix.system_commit()
            assert_boot(rugix, default="a", active="a")
        else:
            target_check = ["test", "-e", target_index]
            if not compute_missing_indices:
                target_check.insert(1, "!")
            amd64_vm.run(target_check, hide=True)
            amd64_vm.run(["test", "-e", source_index], hide=True)
            assert_boot(rugix, default="a", active="b")
