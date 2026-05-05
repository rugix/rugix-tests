"""Port of ``tests/tests/test-update-index-http.toml``.

Uses the in-VM nginx (installed by the ``hello-world`` recipe) to serve a
delta bundle over ``http://localhost``, exercising the HTTP fetch path of
``rugix-ctrl update install``. Reboots via ``rugix-ctrl system reboot
--spare`` after the install (the install itself uses ``--reboot no``).
"""

from __future__ import annotations

import pytest

from conftest import assert_boot
from harness import BakeryBuilder
from rugix_testkit import RugixCtrl, VMHandle

REMOTE_BUNDLE = "/var/www/html/system.rugixb"
INDEX_FILE = (
    "/run/rugix/mounts/data/rugix/slots/system-a/casync-64_sha512-256.rugix-block-index"
)


@pytest.mark.slow
def test_update_index_http(
    amd64_vm: VMHandle,
    rugix: RugixCtrl,
    bakery: BakeryBuilder,
) -> None:
    amd64_vm.run(
        ["rugix-ctrl", "slots", "create-index", "system-a", "casync-64", "sha512-256"],
        hide=True,
    )
    amd64_vm.run(["test", "-e", INDEX_FILE], hide=True)
    assert_boot(rugix, default="a", active="a")

    delta_base = bakery.bake_bundle("customized-amd64-delta")
    amd64_vm.upload(delta_base, REMOTE_BUNDLE)
    amd64_vm.run(["chmod", "777", REMOTE_BUNDLE], hide=True)

    rugix.update_install("http://localhost/system.rugixb", timeout=600)

    try:
        amd64_vm.run(
            ["rugix-ctrl", "system", "reboot", "--spare"], check=False, hide=True
        )
    except Exception:
        pass
    amd64_vm.wait_for_reboot()

    assert_boot(rugix, default="a", active="b")
    rugix.system_commit()
    assert_boot(rugix, default="b", active="b")
