"""End-to-end tests for Rugix init error shell handling."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from rugix_testkit import QemuVM

from harness import BakeryBuilder, build_amd64_vm_config


@pytest.fixture(autouse=True, scope="module")
def clear_init_error_shell_build_outputs() -> None:
    """Force init error shell images to be rebuilt for this module."""
    repo = Path(__file__).resolve().parents[2]
    project = repo / "tests"
    for system in ("init-error-shell-disabled", "init-error-shell-enabled"):
        output = project / "build" / system
        if output.exists():
            shutil.rmtree(output)


@pytest.mark.slow
def test_init_error_without_shell_prints_opt_in_hint(bakery: BakeryBuilder) -> None:
    image = bakery.bake_image("init-error-shell-disabled")
    output = _boot_until_serial(
        image,
        "The init error shell is disabled",
        timeout=180,
    )

    assert "rugix.init.shell_on_error" in output
    assert "Press any key" not in output


@pytest.mark.slow
def test_init_error_shell_starts_after_keypress(bakery: BakeryBuilder) -> None:
    image = bakery.bake_image("init-error-shell-enabled")
    qemu = QemuVM(build_amd64_vm_config(image))
    qemu.prepare()
    qemu.start()
    try:
        qemu.wait_for_serial("Press any key within", timeout=180)
        qemu.write_serial(b"x")
        qemu.wait_for_serial("Starting debug shell.", timeout=30)

        qemu.write_serial(b"echo RUGIX_INIT_ERROR_SHELL_READY\n")
        output = qemu.wait_for_serial("RUGIX_INIT_ERROR_SHELL_READY", timeout=30)
    finally:
        qemu.stop()
        qemu.cleanup()

    assert "Starting debug shell." in output


def _boot_until_serial(image: Path, text: str, *, timeout: float) -> str:
    qemu = QemuVM(build_amd64_vm_config(image))
    qemu.prepare()
    qemu.start()
    try:
        return qemu.wait_for_serial(text, timeout=timeout)
    finally:
        qemu.stop()
        qemu.cleanup()
