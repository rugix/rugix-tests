"""Wrapper around the `run-bakery` shell entry point.

The bake stage runs inside the rugix-bakery container (matching how users
build images in production); the resulting artifacts land on the host under
``build/`` because the project directory is bind-mounted into the container
by ``run-bakery``. Tests then consume those artifacts directly from the host.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BakedSystem:
    """Outputs of ``./run-bakery bake`` for a given system."""

    name: str
    image: Path
    """Boot image (``build/<system>/system.img``). Present for ``bake image``."""

    bundle: Path
    """Update bundle (``build/<system>/system.rugixb``). Present for ``bake bundle``."""


class BakeryBuilder:
    """Drives ``./run-bakery`` from the host, caching results per session.

    The same project directory is shared between the host (where pytest runs)
    and the bakery container (where the actual build happens), so artifacts
    appear at predictable paths under ``project_dir / "build"``.
    """

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir.resolve()
        self._image_cache: dict[str, Path] = {}
        self._bundle_cache: dict[str, Path] = {}
        self._lock = Lock()

    def bake_image(self, system: str, *, force: bool = False) -> Path:
        """Bake a boot image. Returns the path to ``system.img`` on the host."""
        with self._lock:
            cached = self._image_cache.get(system)
            if cached is not None and not force:
                return cached

            self._run_bakery(["bake", "image", system])
            image = self.project_dir / "build" / system / "system.img"
            if not image.exists():
                raise FileNotFoundError(
                    f"bake image {system!r} did not produce {image}"
                )
            self._image_cache[system] = image
            return image

    def bake_bundle(self, system: str, *, force: bool = False) -> Path:
        """Bake an update bundle. Returns the path to ``system.rugixb``."""
        with self._lock:
            cached = self._bundle_cache.get(system)
            if cached is not None and not force:
                return cached

            self._run_bakery(["bake", "bundle", system])
            bundle = self.project_dir / "build" / system / "system.rugixb"
            if not bundle.exists():
                raise FileNotFoundError(
                    f"bake bundle {system!r} did not produce {bundle}"
                )
            self._bundle_cache[system] = bundle
            return bundle

    def baked(self, system: str) -> BakedSystem:
        """Bake both the image and the bundle for *system* and return the paths."""
        return BakedSystem(
            name=system,
            image=self.bake_image(system),
            bundle=self.bake_bundle(system),
        )

    def _run_bakery(self, args: list[str]) -> None:
        cmd = ["./run-bakery", *args]
        logger.info("bakery: %s", " ".join(cmd))
        env = os.environ.copy()
        env.setdefault("RUGIX_DEV", "true")
        subprocess.run(cmd, cwd=self.project_dir, check=True, env=env)
