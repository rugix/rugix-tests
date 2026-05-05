"""Port of ``tests/tests/test-update-bundle.toml``.

Drives three A/B update cycles after asserting the bundle is rejected
without ``--insecure-skip-bundle-verification``.
"""

from __future__ import annotations

import pytest

from conftest import assert_boot, install_and_reboot
from harness import BakeryBuilder
from rugix_testkit import CmdError, RugixCtrl, VMHandle


@pytest.mark.slow
def test_update_bundle(
    amd64_vm: VMHandle,
    rugix: RugixCtrl,
    bakery: BakeryBuilder,
) -> None:
    bundle = bakery.bake_bundle("customized-amd64")

    # Install must fail without --insecure-skip-bundle-verification.
    with pytest.raises(CmdError):
        rugix.update_install_file(bundle, insecure=False, timeout=300)

    assert_boot(rugix, default="a", active="a")

    expected = [
        ("a", "b", "b"),
        ("b", "a", "a"),
        ("a", "b", "b"),
    ]
    for default_before, active, default_after in expected:
        install_and_reboot(rugix, bundle)
        assert_boot(rugix, default=default_before, active=active)
        rugix.system_commit()
        assert_boot(rugix, default=default_after, active=active)
