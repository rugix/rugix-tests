"""Bakery-specific QEMU configuration helpers.

The runtime VM management lives in :mod:`rugix_testkit`; this module just
encodes how rugix-bakery's amd64 images expect to be booted (q35 + OVMF
pflash + virtio drive overlay).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from rugix_testkit import Drive, Pflash, VMConfig


def build_amd64_vm_config(image: Path, *, disk_size: str = "40G") -> VMConfig:
    """Build a :class:`VMConfig` for booting an amd64 ``generic-grub-efi`` image.

    Uses ``-machine q35`` with OVMF supplied as pflash (the standard QEMU
    setup for the 4MB-layout OVMF that nix's ``qemu`` package ships).
    rugix-bakery itself uses ``-machine pc`` with ``-bios`` because its
    container ships the legacy 2MB ``OVMF_CODE.fd``; the image is plain
    UEFI grub, so it boots fine under either machine.
    """
    code, vars_ = _ovmf_paths_amd64()
    return VMConfig(
        arch="x86_64",
        memory=2048,
        smp=2,
        drives=[
            Drive(
                file=image,
                format="raw",
                interface="virtio",
                overlay=True,
                size=disk_size,
            ),
        ],
        pflash=[
            Pflash(file=code, format="raw", readonly=True),
            Pflash(file=vars_, format="raw", readonly=False),
        ],
        extra_args=["-device", "virtio-rng-pci"],
    )


def _ovmf_paths_amd64() -> tuple[Path, Path]:
    """Resolve OVMF code and vars firmware paths.

    Env var overrides (matching rugix-bakery's convention):
    ``RUGIX_OVMF_CODE_AMD64`` for the code blob, ``RUGIX_OVMF_VARS_AMD64``
    for the vars blob. Otherwise look next to ``qemu-system-x86_64`` on
    PATH, then fall back to standard Debian package paths.
    """
    code = _resolve_ovmf(
        env="RUGIX_OVMF_CODE_AMD64",
        qemu_share=("edk2-x86_64-code.fd",),
        system=(
            "/usr/share/OVMF/OVMF_CODE_4M.fd",
            "/usr/share/OVMF/OVMF_CODE.fd",
        ),
        kind="code",
    )
    vars_ = _resolve_ovmf(
        env="RUGIX_OVMF_VARS_AMD64",
        qemu_share=("edk2-i386-vars.fd",),
        system=(
            "/usr/share/OVMF/OVMF_VARS_4M.fd",
            "/usr/share/OVMF/OVMF_VARS.fd",
        ),
        kind="vars",
    )
    return code, vars_


def _resolve_ovmf(
    *,
    env: str,
    qemu_share: tuple[str, ...],
    system: tuple[str, ...],
    kind: str,
) -> Path:
    override = os.environ.get(env)
    if override:
        return Path(override)

    qemu = shutil.which("qemu-system-x86_64")
    if qemu is not None:
        share = Path(qemu).resolve().parent.parent / "share/qemu"
        for name in qemu_share:
            candidate = share / name
            if candidate.exists():
                return candidate

    for path in system:
        if Path(path).exists():
            return Path(path)

    raise FileNotFoundError(
        f"Could not locate OVMF {kind} firmware. Set {env} to the file path."
    )
