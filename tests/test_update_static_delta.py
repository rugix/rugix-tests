"""Port of ``tests/tests/test-update-static-delta.toml``.

Two-step update: first installs the regular ``customized-amd64`` bundle,
commits, then installs a static-delta bundle (built via ``bundler delta``
from the base and ``customized-amd64-delta``) and commits again.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import assert_boot, install_and_reboot
from harness import BakeryBuilder
from rugix_testkit import RugixCtrl, VMHandle


@pytest.fixture(scope="session")
def delta_bundle(bakery: BakeryBuilder, project_dir: Path) -> Path:
    base = bakery.bake_bundle("customized-amd64")
    target = bakery.bake_bundle("customized-amd64-delta")
    output = project_dir / "build" / "delta.rugixb"
    if not output.exists():
        bakery.bundler_delta(base, target, output)
    return output


@pytest.mark.slow
def test_update_static_delta(
    amd64_vm: VMHandle,
    rugix: RugixCtrl,
    bakery: BakeryBuilder,
    delta_bundle: Path,
) -> None:
    base_bundle = bakery.bake_bundle("customized-amd64")

    assert_boot(rugix, default="a", active="a")

    install_and_reboot(rugix, base_bundle)
    assert_boot(rugix, default="a", active="b")
    rugix.system_commit()
    assert_boot(rugix, default="b", active="b")

    install_and_reboot(rugix, delta_bundle)
    assert_boot(rugix, default="b", active="a")
    rugix.system_commit()
    assert_boot(rugix, default="a", active="a")
