"""End-to-end coverage for the privileged Rugix Ctrl daemon bridge."""

from __future__ import annotations

from pathlib import Path

import pytest
from rugix_testkit import CmdError, RugixCtrl, VMHandle

from conftest import assert_boot
from harness import BakeryBuilder

CTRL_CONFIG = """\
[signatures]
roots = ["/etc/rugix/root.crt"]
"""

DAEMON_CONFIG = """\
socket-path = "/run/rugix/ctrl.sock"
dangerously-insecure = false
"""
REMOTE_BUNDLE = "/tmp/rugix-ctrl-daemon-update.rugixb"
REJECTED_BUNDLE = "/tmp/rugix-ctrl-daemon-rejected.rugixb"


@pytest.fixture(scope="session")
def daemon_signed_bundle(bakery: BakeryBuilder, project_dir: Path) -> Path:
    base = bakery.bake_bundle("customized-amd64")
    output = project_dir / "build" / "customized-amd64-daemon-signed.rugixb"
    if not output.exists():
        bakery.bundler_sign(
            base,
            project_dir / "keys" / "signer.crt",
            project_dir / "keys" / "signer.key",
            output,
        )
    return output


@pytest.fixture
def ctrl_daemon_vm(amd64_vm: VMHandle) -> VMHandle:
    amd64_vm.run(
        [
            "sh",
            "-c",
            (
                f"cat > /etc/rugix/ctrl.toml <<'TOML'\n{CTRL_CONFIG}TOML\n"
                f"cat > /etc/rugix/daemon.toml <<'TOML'\n{DAEMON_CONFIG}TOML"
            ),
        ],
        hide=True,
    )
    amd64_vm.run(
        [
            "sh",
            "-c",
            (
                "getent group rugix-admin >/dev/null || "
                "groupadd --system rugix-admin; "
                "id rugix-admin >/dev/null 2>&1 || "
                "useradd --system --gid rugix-admin --no-create-home rugix-admin; "
                "rugix-ctrl daemon >/tmp/rugix-ctrl-daemon.log 2>&1 & "
                "echo $! >/tmp/rugix-ctrl-daemon.pid; "
                "for attempt in $(seq 1 100); do "
                "[ -S /run/rugix/ctrl.sock ] && break; sleep 0.1; "
                "done; "
                "test -S /run/rugix/ctrl.sock; "
                "chgrp rugix-admin /run/rugix/ctrl.sock"
            ),
        ],
        hide=True,
    )
    return amd64_vm


@pytest.mark.slow
def test_ctrl_daemon_update_installation(
    ctrl_daemon_vm: VMHandle,
    rugix: RugixCtrl,
    daemon_signed_bundle: Path,
) -> None:
    assert_boot(rugix, default="a", active="a")

    ctrl_daemon_vm.upload(daemon_signed_bundle, REMOTE_BUNDLE)
    ctrl_daemon_vm.run(["chmod", "644", REMOTE_BUNDLE], hide=True)
    ctrl_daemon_vm.run(
        [
            "runuser",
            "-u",
            "rugix-admin",
            "--",
            "rugix-ctrl",
            "update",
            "install",
            "--reboot",
            "no",
            REMOTE_BUNDLE,
        ],
        timeout=600,
        hide=True,
    )
    assert_boot(rugix, default="a", active="a")

    ctrl_daemon_vm.run(
        [
            "sh",
            "-c",
            (
                "nohup sh -c 'sleep 1; rugix-ctrl system reboot --spare' "
                ">/tmp/rugix-ctrl-reboot.log 2>&1 </dev/null &"
            ),
        ],
        hide=True,
    )
    ctrl_daemon_vm.wait_for_reboot()

    assert_boot(rugix, default="a", active="b")


@pytest.mark.slow
def test_ctrl_daemon_query_and_admission_policy(
    ctrl_daemon_vm: VMHandle,
) -> None:
    info = ctrl_daemon_vm.run_json(
        [
            "runuser",
            "-u",
            "rugix-admin",
            "--",
            "rugix-ctrl",
            "system",
            "info",
            "--json",
        ]
    )
    assert info["boot"]["activeGroup"] == "a"
    assert info["boot"]["defaultGroup"] == "a"

    ctrl_daemon_vm.run(["touch", REJECTED_BUNDLE], hide=True)
    ctrl_daemon_vm.run(["chmod", "644", REJECTED_BUNDLE], hide=True)
    with pytest.raises(CmdError) as insecure_install:
        ctrl_daemon_vm.run(
            [
                "runuser",
                "-u",
                "rugix-admin",
                "--",
                "rugix-ctrl",
                "update",
                "install",
                "--reboot",
                "no",
                "--insecure-skip-bundle-verification",
                REJECTED_BUNDLE,
            ],
            timeout=300,
            hide=True,
        )
    assert "dangerously-insecure = true" in insecure_install.value.result.stderr

    with pytest.raises(CmdError) as system_commit:
        ctrl_daemon_vm.run(
            [
                "runuser",
                "-u",
                "rugix-admin",
                "--",
                "rugix-ctrl",
                "system",
                "commit",
            ],
            hide=True,
        )
    assert "features.system-commit = true" in system_commit.value.result.stderr
