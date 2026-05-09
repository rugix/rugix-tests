"""Bakery-specific test harness for the Rugix system tests.

Wraps ``./run-bakery`` (image + bundle + bundler invocations) and provides
the amd64 VMConfig that matches rugix-bakery's image conventions. The
runtime VM and SSH bits live in :mod:`rugix_testkit`.
"""

from harness.bakery import BakedSystem, BakeryBuilder
from harness.vm import (
    SwtpmProcess,
    build_amd64_vm_config,
    build_amd64_vm_config_with_tpm,
)

__all__ = [
    "BakedSystem",
    "BakeryBuilder",
    "SwtpmProcess",
    "build_amd64_vm_config",
    "build_amd64_vm_config_with_tpm",
]
