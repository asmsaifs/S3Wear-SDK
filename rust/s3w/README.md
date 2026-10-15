# s3w

Safe Rust wrappers over the S3Wear mini app API, for `no_std` apps compiled to `wasm32-unknown-unknown`
and run on the S3Wear smartwatch (ESP32-S3, 466×466 AMOLED).

Covers logging, time, timers, widgets, canvas, key-value storage, game services and events. Anything
else is reachable through `s3w::sys` (the raw bindings from the `s3w-sys` crate).

## Use

Start from a template; the `s3w` CLI sets up the target flags the watch runtime needs:

```bash
pipx install s3w
s3w new my-app --lang rust
s3w build my-app
s3w run-sim my-app
```

An app is a `cdylib` that calls `s3w::export_event_buf!()` once and defines the lifecycle exports it
uses (`s3w_on_start`, `s3w_on_event`, `s3w_on_frame`, ...).

```toml
[lib]
crate-type = ["cdylib"]

[dependencies]
s3w = "0.1"
```

Building by hand needs `rustup target add wasm32-unknown-unknown` and the flags
`-C target-cpu=mvp -C target-feature=+bulk-memory,+sign-ext,+nontrapping-fptoint,+mutable-globals`:
the watch's runtime has no reference types, which rustc enables by default. `s3w build` passes them.

Documentation: <https://s3wear.fiqraat.com/developers/> · Source:
<https://github.com/asmsaifs/S3Wear-SDK>

## Versions

Crate version is `0.<api_level>.<patch>`: `0.1.x` targets api_level 1.

Apache-2.0.
