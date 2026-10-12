# Rugix Tests

Shared integration test infrastructure for the [Rugix](https://rugix.org) project.

> [!NOTE]
> **Support:** This is internal test infrastructure. It is not intended for
> general use, and its interfaces may change without notice.

[Rugix Ctrl](https://github.com/rugix/rugix) and [Rugix Bakery](https://github.com/rugix/rugix-bakery) live in separate repositories to enable independent release cycles. Testing Rugix Ctrl requires building complete system images to test actual updates in VMs, which is done using Rugix Bakery. To this end, this repository provides a shared test suite that both projects include as a submodule, allowing us to validate changes in both tools against a unified, comprehensive set of tests.

## Running the Tests

The system tests use pytest and [`rugix-testkit`](https://github.com/rugix/rugix-testkit). Bakery builds OS images and system bundles in its container. App packing, bundle signing, static delta creation, and QEMU run on the host.

Prerequisites:

- A container runtime (`podman` or `docker`) for the bake stage.
- A host `rugix-bundler` binary, selected with `RUGIX_BUNDLER` or found on PATH.
- `skopeo` for bundling Compose images and `xdelta3` for static deltas. Compose builds also require Docker or Podman on the host.
- `qemu-system-x86_64` and OVMF firmware on PATH (system packages, e.g. `qemu` from your distro or `nix-shell -p qemu`).
- `mise`, which installs Python and `uv`. `rugix-testkit` and the other Python dependencies are fetched on first run.

```bash
./generate-test-keys.sh
mise install
mise run check    # lint + typecheck + tests
mise run test     # tests only
```

Per-test artifacts (serial console, command history) land under `test-outputs/<nodeid>/`.

A few tests carry the `extended` marker (deb-package install variants, system-state persistence) and are skipped by default. Set `RUGIX_TESTS_EXTENDED=1` to run them.

The pytest entrypoint sets `RUGIX_BINARIES_DIR=../build/binaries` when that directory exists and the variable is unset. Bakery mounts those binaries to install the current Ctrl into OS images. On Linux amd64 and arm64 hosts, Bundler also selects the matching musl binary from that directory. A missing selected binary fails the operation instead of falling back to another version.

`RUGIX_BUNDLER` overrides that selection. For example, run against a specific build with:

```bash
RUGIX_BUNDLER=/path/to/rugix-bundler mise run test tests/test_apps_configuration.py
```

Bakery CI selects its Bundler build artifact explicitly while the OS images use the Ctrl embedded in the Bakery image.

## Licensing

This project is licensed under either [MIT](https://github.com/rugix/rugix/blob/main/LICENSE-MIT) or [Apache 2.0](https://github.com/rugix/rugix/blob/main/LICENSE-APACHE) at your option.

Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in this project by you, as defined in the Apache 2.0 license, shall be dual licensed as above, without any additional terms or conditions.

---

Made with ❤️ for OSS by [Silitics](https://www.silitics.com)
