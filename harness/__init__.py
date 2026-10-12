"""Build and VM harness for the Rugix system tests.

Bakes OS images with ``./run-bakery``, runs Bundler on the host, and provides
the amd64 VMConfig that matches rugix-bakery's image conventions. The
runtime VM and SSH bits live in :mod:`rugix_testkit`.
"""

from harness.bakery import BakedSystem, BakeryBuilder
from harness.bundler import Bundler
from harness.vm import (
    SwtpmProcess,
    build_amd64_vm_config,
    build_amd64_vm_config_with_tpm,
)

__all__ = [
    "BakedSystem",
    "BakeryBuilder",
    "Bundler",
    "SwtpmProcess",
    "build_amd64_vm_config",
    "build_amd64_vm_config_with_tpm",
]
