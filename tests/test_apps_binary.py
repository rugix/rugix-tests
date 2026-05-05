"""Port of ``tests/tests/test-apps-binary.toml``.

Boots ``customized-amd64-docker``, packs the ``hello-binary`` app from
``apps/binary-hello/`` via ``bundler apps pack binary`` (one-shot binary
served by a systemd unit), and walks through install → activate/deactivate
→ reboot → remove.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from harness import BakeryBuilder
from rugix_testkit import VMHandle

REMOTE_BUNDLE = "/tmp/binary-hello.rugixb"
APP_NAME = "hello-binary"


@pytest.fixture
def boot_system() -> str:
    return "customized-amd64-docker"


@pytest.fixture
def boot_timeout() -> float:
    # Docker host boots slower than the regular customized-amd64.
    return 600.0


@pytest.fixture(scope="session")
def binary_app_bundle(bakery: BakeryBuilder, project_dir: Path) -> Path:
    output = project_dir / "apps" / "build" / "binary-hello_amd64.rugixb"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    bakery.bundler_apps_pack(
        "binary",
        [
            "--app",
            APP_NAME,
            "--service",
            "apps/binary-hello/hello-server.service",
        ],
        project_dir / "apps" / "binary-hello" / "hello-server",
        output,
    )
    return output


@pytest.mark.slow
def test_apps_binary(
    amd64_vm: VMHandle,
    binary_app_bundle: Path,
) -> None:
    _assert_no_apps(amd64_vm)

    amd64_vm.upload(binary_app_bundle, REMOTE_BUNDLE)
    amd64_vm.run(
        [
            "rugix-ctrl",
            "apps",
            "install",
            "--insecure-skip-bundle-verification",
            REMOTE_BUNDLE,
        ],
        timeout=300,
        hide=True,
    )
    _wait(amd64_vm, 3)

    apps = amd64_vm.run_json(["rugix-ctrl", "apps", "list"])
    app = apps[APP_NAME]
    assert isinstance(app, dict)
    assert app["status"]["state"] == "running"
    assert app["generation"] == 1

    marker = amd64_vm.run(
        ["cat", f"/run/rugix/state/apps/{APP_NAME}/data/running"], hide=True
    ).stdout.strip()
    assert marker == APP_NAME

    amd64_vm.run(["systemctl", "is-active", f"rugix-app-{APP_NAME}.service"], hide=True)

    info = amd64_vm.run_json(["rugix-ctrl", "apps", "info", APP_NAME])
    assert info["name"] == APP_NAME
    assert info["state"]["state"] == "active"
    assert info["state"]["generation"] == 1
    assert isinstance(info["generations"], list) and len(info["generations"]) == 1
    assert info["generations"][0]["active"] is True

    amd64_vm.run(["rugix-ctrl", "apps", "deactivate", APP_NAME], hide=True)

    apps = amd64_vm.run_json(["rugix-ctrl", "apps", "list"])
    assert apps[APP_NAME]["status"]["state"] == "stopped"
    # ``jq '.x == null'`` returns true for both null and missing keys; mirror
    # that with ``.get`` so a missing field passes alongside an explicit null.
    assert apps[APP_NAME].get("generation") is None

    res = amd64_vm.run(
        ["test", "-f", f"/run/rugix/state/apps/{APP_NAME}/data/running"],
        check=False,
        hide=True,
    )
    assert not res.ok

    amd64_vm.run(["rugix-ctrl", "apps", "activate", APP_NAME, "1"], hide=True)
    _wait(amd64_vm, 3)

    apps = amd64_vm.run_json(["rugix-ctrl", "apps", "list"])
    assert apps[APP_NAME]["status"]["state"] == "running"

    try:
        amd64_vm.run(["reboot"], check=False, hide=True)
    except Exception:
        pass
    amd64_vm.wait_for_reboot()
    _wait(amd64_vm, 10)

    apps = amd64_vm.run_json(["rugix-ctrl", "apps", "list"])
    assert apps[APP_NAME]["status"]["state"] == "running"
    assert apps[APP_NAME]["generation"] == 1
    amd64_vm.run(["systemctl", "is-active", f"rugix-app-{APP_NAME}.service"], hide=True)
    marker = amd64_vm.run(
        ["cat", f"/run/rugix/state/apps/{APP_NAME}/data/running"], hide=True
    ).stdout.strip()
    assert marker == APP_NAME

    amd64_vm.run(["rugix-ctrl", "apps", "remove", APP_NAME], hide=True)
    _assert_no_apps(amd64_vm)


def _assert_no_apps(vm: VMHandle) -> None:
    apps = vm.run_json(["rugix-ctrl", "apps", "list"])
    assert isinstance(apps, dict) and len(apps) == 0


def _wait(vm: VMHandle, seconds: int) -> None:
    vm.run(["sleep", str(seconds)], hide=True)
