# Rugix Tests

Shared integration test infrastructure for the [Rugix](https://rugix.org) project.

[Rugix Ctrl](https://github.com/rugix/rugix) and [Rugix Bakery](https://github.com/rugix/rugix-bakery) live in separate repositories to enable independent release cycles. Testing Rugix Ctrl requires building complete system images to test actual updates in VMs, which is done using Rugix Bakery. To this end, this repository provides a shared test suite that both projects include as a submodule, allowing us to validate changes in both tools against a unified, comprehensive set of tests.

## ⚖️ Licensing

This project is licensed under either [MIT](https://github.com/rugix/rugix/blob/main/LICENSE-MIT) or [Apache 2.0](https://github.com/rugix/rugix/blob/main/LICENSE-APACHE) at your option.

Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in this project by you, as defined in the Apache 2.0 license, shall be dual licensed as above, without any additional terms or conditions.

---

Made with ❤️ for OSS by [Silitics](https://www.silitics.com)
