"""Device-specific application configuration across app generations.

Boots ``customized-amd64-docker`` and walks the ``hello-config`` app through
the configuration lifecycle: the bundled default applies until the device sets
its own document, an unchanged document does not restart the workload, a
generation whose schema no longer accepts the stored document is refused
without disturbing the running app, ``apps activate --config`` takes that
generation over with a matching document, and rollback restores the generation
together with the revision it ran.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from harness import BakeryBuilder
from rugix_testkit import VMHandle

APP_NAME = "hello-config"

DEVICE_CONFIG = {"endpoint": "https://device.example.com"}
DEVICE_CONFIG_V2 = {"endpoint": "https://device.example.com", "token": "device-token"}

DEVICE_CONFIG_PATH = "/tmp/hello-config.json"
DEVICE_CONFIG_V2_PATH = "/tmp/hello-config-v2.json"


@pytest.fixture
def boot_system() -> str:
    return "customized-amd64-docker"


@pytest.fixture
def boot_timeout() -> float:
    return 600.0


@pytest.fixture(scope="session")
def app_dir(project_dir: Path) -> Path:
    return project_dir / "apps" / "generic-config"


def _pack(
    bakery: BakeryBuilder,
    app_dir: Path,
    project_dir: Path,
    *,
    label: str,
    schema: str,
    default: str,
) -> Path:
    output = project_dir / "apps" / "build" / f"generic-config_{label}_amd64.rugixb"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    bakery.bundler_apps_pack(
        "generic",
        [
            "--app",
            APP_NAME,
            "--config-schema",
            str((app_dir / schema).relative_to(project_dir)),
            "--config-default",
            str((app_dir / default).relative_to(project_dir)),
        ],
        app_dir / "orchestrator",
        output,
    )
    return output


@pytest.fixture(scope="session")
def app_bundle_v1(bakery: BakeryBuilder, app_dir: Path, project_dir: Path) -> Path:
    """Bundle whose schema requires only ``endpoint``."""
    return _pack(
        bakery,
        app_dir,
        project_dir,
        label="v1",
        schema="config.schema.json",
        default="config.default.json",
    )


@pytest.fixture(scope="session")
def app_bundle_v2(bakery: BakeryBuilder, app_dir: Path, project_dir: Path) -> Path:
    """Bundle whose schema additionally requires ``token``."""
    return _pack(
        bakery,
        app_dir,
        project_dir,
        label="v2",
        schema="config.schema.v2.json",
        default="config.default.v2.json",
    )


@pytest.mark.slow
def test_apps_configuration(
    amd64_vm: VMHandle,
    app_bundle_v1: Path,
    app_bundle_v2: Path,
    bundle_url: Callable[[Path], str],
) -> None:
    _install(amd64_vm, bundle_url(app_bundle_v1))

    # Without a device-specific document, the bundled default applies.
    assert _applied_config(amd64_vm) == {"endpoint": "https://default.example.com"}
    assert _config_get(amd64_vm) == {"endpoint": "https://default.example.com"}
    assert _generation(amd64_vm) == 1
    assert _configuration_revision(amd64_vm) is None

    _write_json(amd64_vm, DEVICE_CONFIG_PATH, DEVICE_CONFIG)
    assert _config_set(amd64_vm, DEVICE_CONFIG_PATH) == 1
    assert _applied_config(amd64_vm) == DEVICE_CONFIG
    assert _configuration_revision(amd64_vm) == 1

    # Re-applying the same document reuses its revision and leaves the running
    # workload in place.
    pid = _workload_pid(amd64_vm)
    assert _config_set(amd64_vm, DEVICE_CONFIG_PATH) == 1
    assert _workload_pid(amd64_vm) == pid

    # Generation 2 requires ``token``, which the stored document does not have, so
    # the installation is refused and the app keeps running generation 1.
    result = amd64_vm.run(
        [
            "rugix-ctrl",
            "apps",
            "install",
            "--insecure-skip-bundle-verification",
            bundle_url(app_bundle_v2),
        ],
        check=False,
        timeout=300,
        hide=True,
    )
    assert not result.ok
    assert _generation(amd64_vm) == 1
    assert _configuration_revision(amd64_vm) == 1
    assert _applied_config(amd64_vm) == DEVICE_CONFIG
    assert _status(amd64_vm) == "running"

    # The refused generation was installed completely, so it can be taken over
    # with a matching document without downloading the bundle again.
    generations = {entry["number"]: entry for entry in _info(amd64_vm)["generations"]}
    assert generations[2]["complete"]
    assert not generations[2]["active"]

    _write_json(amd64_vm, DEVICE_CONFIG_V2_PATH, DEVICE_CONFIG_V2)
    amd64_vm.run(
        [
            "rugix-ctrl",
            "apps",
            "activate",
            APP_NAME,
            "2",
            "--config",
            DEVICE_CONFIG_V2_PATH,
        ],
        timeout=120,
        hide=True,
    )
    _wait(amd64_vm, 3)
    assert _generation(amd64_vm) == 2
    assert _configuration_revision(amd64_vm) == 2
    assert _applied_config(amd64_vm) == DEVICE_CONFIG_V2
    assert _status(amd64_vm) == "running"

    # Rollback restores generation 1 together with the revision it ran, rather
    # than the newest revision, which generation 1's schema would reject.
    amd64_vm.run(["rugix-ctrl", "apps", "rollback", APP_NAME], timeout=120, hide=True)
    _wait(amd64_vm, 3)
    assert _generation(amd64_vm) == 1
    assert _configuration_revision(amd64_vm) == 1
    assert _applied_config(amd64_vm) == DEVICE_CONFIG
    assert _status(amd64_vm) == "running"


def _install(vm: VMHandle, url: str) -> None:
    vm.run(
        ["rugix-ctrl", "apps", "install", "--insecure-skip-bundle-verification", url],
        timeout=300,
        hide=True,
    )
    _wait(vm, 3)


def _write_json(vm: VMHandle, path: str, document: dict[str, Any]) -> None:
    script = f"cat > {path} <<'EOF_CONFIG'\n{json.dumps(document)}\nEOF_CONFIG\n"
    vm.run(["sh", "-c", script], hide=True)


def _config_set(vm: VMHandle, path: str) -> Any:
    output = vm.run_json(["rugix-ctrl", "apps", "config", "set", APP_NAME, path])
    return output["revision"]


def _config_get(vm: VMHandle) -> Any:
    return vm.run_json(["rugix-ctrl", "apps", "config", "get", APP_NAME])


def _info(vm: VMHandle) -> Any:
    return vm.run_json(["rugix-ctrl", "apps", "info", APP_NAME])


def _generation(vm: VMHandle) -> Any:
    return vm.run_json(["rugix-ctrl", "apps", "list"])[APP_NAME].get("generation")


def _status(vm: VMHandle) -> Any:
    return vm.run_json(["rugix-ctrl", "apps", "list"])[APP_NAME]["status"]["state"]


def _configuration_revision(vm: VMHandle) -> Any:
    return _info(vm)["state"].get("configurationRevision")


def _applied_config(vm: VMHandle) -> Any:
    path = f"/run/rugix/state/apps/{APP_NAME}/data/applied-config.json"
    return json.loads(vm.run(["cat", path], hide=True).stdout)


def _workload_pid(vm: VMHandle) -> str:
    path = f"/run/rugix/state/apps/{APP_NAME}/data/pid"
    return vm.run(["cat", path], hide=True).stdout.strip()


def _wait(vm: VMHandle, seconds: int) -> None:
    vm.run(["sleep", str(seconds)], hide=True)
