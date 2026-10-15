# s3w-sys

Raw bindings to the S3Wear mini app API (`s3w.h`, api_level 1) for `wasm32-unknown-unknown` apps that run
on the S3Wear smartwatch. Generated from the header; do not edit `src/lib.rs` by hand.

Most apps want the safe wrappers in the [`s3w`](https://crates.io/crates/s3w) crate, which re-exports this
one as `s3w::sys`.

Documentation: <https://s3wear.fiqraat.com/developers/> · Source:
<https://github.com/asmsaifs/S3Wear-SDK>

Crate version is `0.<api_level>.<patch>`. Apache-2.0.
