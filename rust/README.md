# Rust SDK

- `s3w-sys`: raw bindings, generated from `sdk/include/s3w.h` by `s3w-sys/gen.py` (do not edit `src/lib.rs`;
  re-run the script after changing the header — the CLI tests check it is fresh).
- `s3w`: safe wrappers for the common parts (log, time, timers, widgets, canvas, key-value storage, game services, events),
  the panic handler and the `s3w::export_event_buf!()` macro every app calls once. Anything else: `s3w::sys`.

Apps are `no_std` `cdylib`s for `wasm32-unknown-unknown` (`rustup target add wasm32-unknown-unknown`), built by
`s3w build` (`sdk/tools/s3w-cli`), which passes `-C target-cpu=mvp` plus the features WAMR supports: the watch's
runtime has no reference types, which rustc enables by default. Start from `s3w new <dir> --lang rust`.
