"""Bakery-specific QEMU configuration helpers.

The runtime VM management lives in :mod:`rugix_testkit`; this module just
encodes how rugix-bakery's amd64 images expect to be booted (q35 + OVMF
pflash + virtio drive overlay), plus optional swtpm-emulated TPM 2.0
support for testing the TPM-backed data partition driver.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from rugix_testkit import Drive, Pflash, VMConfig

logger = logging.getLogger(__name__)


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


class SwtpmProcess:
    """An ephemeral swtpm 2.0 process, exposing a Unix socket for QEMU.

    Used as a context manager so the TPM is torn down with the VM. The
    state directory is created under a tempdir and cleaned up on exit.
    """

    def __init__(self, *, swtpm_binary: str = "swtpm") -> None:
        self.swtpm_binary = shutil.which(swtpm_binary) or os.environ.get(
            "RUGIX_SWTPM_BINARY", swtpm_binary
        )
        self._tmpdir: tempfile.TemporaryDirectory[str] | None = None
        self._process: subprocess.Popen[bytes] | None = None
        self._state_dir: Path | None = None
        self._socket_path: Path | None = None

    @property
    def socket_path(self) -> Path:
        assert self._socket_path is not None, "SwtpmProcess not started"
        return self._socket_path

    def __enter__(self) -> SwtpmProcess:
        self._tmpdir = tempfile.TemporaryDirectory(prefix="rugix-swtpm-")
        root = Path(self._tmpdir.name)
        self._state_dir = root / "state"
        self._state_dir.mkdir()
        self._socket_path = root / "ctrl.sock"

        # Provision an empty TPM 2.0 state. We deliberately skip
        # `--create-ek-cert` / `--create-platform-cert` here: those invoke
        # swtpm_localca, which needs a system-level writable statedir that
        # rootless setups can't provide. systemd-cryptenroll seals directly
        # to TPM key material without consulting EK certs, so the test runs
        # fine without a cert chain.
        setup_binary = (
            shutil.which("swtpm_setup") if self.swtpm_binary else None
        ) or "swtpm_setup"
        subprocess.run(
            [
                setup_binary,
                "--tpm2",
                "--tpm-state",
                str(self._state_dir),
            ],
            check=True,
            capture_output=True,
        )

        # Start swtpm in socket mode. The Unix-domain control socket is what
        # QEMU connects to via ``-chardev socket,path=...``.
        assert self.swtpm_binary is not None
        self._process = subprocess.Popen(
            [
                self.swtpm_binary,
                "socket",
                "--tpm2",
                "--tpmstate",
                f"dir={self._state_dir}",
                "--ctrl",
                f"type=unixio,path={self._socket_path}",
                "--flags",
                "startup-clear",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for the socket to appear (swtpm creates it asynchronously).
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if self._socket_path.exists():
                logger.info("swtpm: socket ready at %s", self._socket_path)
                return self
            if self._process.poll() is not None:
                stderr = b""
                if self._process.stderr is not None:
                    stderr = self._process.stderr.read()
                raise RuntimeError(
                    f"swtpm exited before its socket appeared: {stderr!r}"
                )
            time.sleep(0.05)
        raise TimeoutError("swtpm socket did not appear within 5 s")

    def __exit__(self, *_exc: object) -> None:
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5)
        self._process = None
        if self._tmpdir is not None:
            self._tmpdir.cleanup()
            self._tmpdir = None


def build_amd64_vm_config_with_tpm(
    image: Path, tpm_socket: Path, *, disk_size: str = "40G"
) -> VMConfig:
    """Like :func:`build_amd64_vm_config`, but with a TPM 2.0 (TIS) device.

    *tpm_socket* is the Unix socket exposed by an already-running swtpm
    instance (see :class:`SwtpmProcess`). The guest sees ``/dev/tpm0`` /
    ``/dev/tpmrm0`` once the kernel's ``tpm_tis`` driver attaches.
    """
    config = build_amd64_vm_config(image, disk_size=disk_size)
    config.extra_args.extend(
        [
            "-chardev",
            f"socket,id=chrtpm,path={tpm_socket}",
            "-tpmdev",
            "emulator,id=tpm0,chardev=chrtpm",
            "-device",
            "tpm-tis,tpmdev=tpm0",
        ]
    )
    return config
