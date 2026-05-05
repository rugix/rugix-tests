"""Port of ``tests/tests/test-update-script.toml``.

Builds ``bundles/script-bundle`` via ``bundler bundle`` and verifies that
installing it leaves the documented marker file under ``/run/rugix/state``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from harness import BakeryBuilder
from rugix_testkit import RugixCtrl, VMHandle

MARKER = "/run/rugix/state/the-update-script-was-here"


@pytest.fixture(scope="session")
def script_bundle(bakery: BakeryBuilder, project_dir: Path) -> Path:
    output = project_dir / "build" / "script-bundle.rugixb"
    if not output.exists():
        bakery.bundler_bundle(project_dir / "bundles" / "script-bundle", output)
    return output


@pytest.mark.slow
def test_update_script(
    amd64_vm: VMHandle,
    rugix: RugixCtrl,
    script_bundle: Path,
) -> None:
    res = amd64_vm.run(["test", "-e", MARKER], check=False, hide=True)
    assert not res.ok, f"{MARKER} must not exist before install"

    rugix.update_install_file(script_bundle)

    amd64_vm.run(["test", "-e", MARKER], hide=True)
