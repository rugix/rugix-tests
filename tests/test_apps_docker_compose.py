"""Port of ``tests/tests/test-apps-docker-compose.toml``.

Packs ``apps/docker-compose-website`` via ``bundler apps pack
docker-compose --pull``, installs into ``customized-amd64-docker``, and
walks through the install / curl / activate / reboot / remove flow.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from harness import BakeryBuilder
from rugix_testkit import VMHandle

REMOTE_BUNDLE = "/tmp/website.rugixb"
APP_NAME = "website"
URL = "http://localhost:8080/"
EXPECTED_BODY = "Hello from Rugix Apps"


@pytest.fixture
def boot_system() -> str:
    return "customized-amd64-docker"


@pytest.fixture
def boot_timeout() -> float:
    return 600.0


@pytest.fixture(scope="session")
def website_bundle(bakery: BakeryBuilder, project_dir: Path) -> Path:
    output = project_dir / "apps" / "build" / "docker-compose-website_amd64.rugixb"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    bakery.bundler_apps_pack(
        "docker-compose",
        [
            "--pull",
            "--platform",
            "linux/amd64",
            "--app",
            APP_NAME,
            "--include",
            "apps/docker-compose-website/www",
        ],
        project_dir / "apps" / "docker-compose-website" / "docker-compose.yml",
        output,
    )
    return output


@pytest.mark.slow
def test_apps_docker_compose(
    amd64_vm: VMHandle,
    website_bundle: Path,
) -> None:
    amd64_vm.run(["docker", "--version"], hide=True)
    amd64_vm.run(["docker", "compose", "version"], hide=True)
    _assert_no_apps(amd64_vm)

    amd64_vm.upload(website_bundle, REMOTE_BUNDLE)
    amd64_vm.run(
        [
            "rugix-ctrl",
            "apps",
            "install",
            "--insecure-skip-bundle-verification",
            REMOTE_BUNDLE,
        ],
        timeout=600,
        hide=True,
    )
    _wait(amd64_vm, 5)

    apps = amd64_vm.run_json(["rugix-ctrl", "apps", "list"])
    assert apps[APP_NAME]["status"]["state"] == "running"
    assert apps[APP_NAME]["generation"] == 1

    _wait(amd64_vm, 2)
    body = amd64_vm.run(["curl", "-sf", URL], hide=True).stdout
    assert EXPECTED_BODY in body

    amd64_vm.run(["rugix-ctrl", "apps", "deactivate", APP_NAME], hide=True)
    apps = amd64_vm.run_json(["rugix-ctrl", "apps", "list"])
    assert apps[APP_NAME]["status"]["state"] == "stopped"

    amd64_vm.run(["rugix-ctrl", "apps", "activate", APP_NAME, "1"], hide=True)
    _wait(amd64_vm, 3)
    body = amd64_vm.run(["curl", "-sf", URL], hide=True).stdout
    assert EXPECTED_BODY in body

    try:
        amd64_vm.run(["reboot"], check=False, hide=True)
    except Exception:
        pass
    amd64_vm.wait_for_reboot()

    # Wait for Docker to come back online.
    amd64_vm.run(
        [
            "sh",
            "-c",
            "for i in $(seq 1 60); do docker info >/dev/null 2>&1 && exit 0; sleep 1; done; exit 1",
        ],
        timeout=120,
        hide=True,
    )
    _wait(amd64_vm, 10)

    apps = amd64_vm.run_json(["rugix-ctrl", "apps", "list"])
    assert apps[APP_NAME]["status"]["state"] == "running"
    body = amd64_vm.run(["curl", "-sf", URL], hide=True).stdout
    assert EXPECTED_BODY in body

    amd64_vm.run(["rugix-ctrl", "apps", "remove", APP_NAME], hide=True)
    _assert_no_apps(amd64_vm)


def _assert_no_apps(vm: VMHandle) -> None:
    apps = vm.run_json(["rugix-ctrl", "apps", "list"])
    assert isinstance(apps, dict) and len(apps) == 0


def _wait(vm: VMHandle, seconds: int) -> None:
    vm.run(["sleep", str(seconds)], hide=True)
