# S3Wear SDK

Build mini apps and watch faces for the S3Wear smartwatch (ESP32-S3, 466×466 AMOLED).
Apps are WebAssembly modules written in C or Rust; faces are data files.

```bash
pipx install s3w            # the CLI (Python 3.9+)
s3w new my-app              # C template; --lang rust for Rust
s3w build my-app            # needs clang with the wasm32 target, or the dev container
s3w run-sim my-app          # needs the simulator: s3w sim install
```

| Folder | Content |
|---|---|
| `include/s3w.h` | the app API (api_level 1) |
| `cli/` | the `s3w` command-line tool |
| `templates/` | project templates used by `s3w new` |
| `rust/` | crates `s3w-sys` (raw bindings) and `s3w` (safe wrappers) |
| `examples/` | small examples and first-party sample apps (`examples/apps/`) |
| `docs/` | the developer documentation |

## Licence

Apache-2.0 for everything in this repository (see [LICENSE](LICENSE)). The simulator binary is
freeware under [SIMULATOR-LICENSE](SIMULATOR-LICENSE) and is not part of this repository.

## Hardware and firmware

Third-party apps run on watches with the Pro firmware. This repository holds no firmware.
