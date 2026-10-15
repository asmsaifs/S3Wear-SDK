# Getting started: a mini app in five minutes

Mini apps are WebAssembly modules that run in a sandbox on the watch. You write them in
C or Rust against one header, `sdk/include/s3w.h`, try them in the desktop simulator and install them on the watch
over USB.

## 1. Tools (once)

| For | Install |
|---|---|
| The CLI | Python ≥ 3.9. `pipx install s3w`, or run `cli/s3w` from a checkout of the SDK repo |
| C apps | a clang with the wasm32 target: `brew install llvm` (macOS), or [wasi-sdk](https://github.com/WebAssembly/wasi-sdk); `CLANG=/path/to/clang` picks one |
| Rust apps | [rustup](https://rustup.rs), then `rustup target add wasm32-unknown-unknown` |
| The simulator | the `s3w_sim` binary (set `S3W_SIM` to its path) |
| Installing on the watch | `pip install pyserial` (pipx installs it with the CLI) |

## 2. A new app, in the simulator

```bash
alias s3w=sdk/tools/s3w-cli/s3w
s3w new apps/counter              # C; --lang rust for Rust; --id dev.you.counter --name "Counter"
s3w run-sim apps/counter          # builds, opens the simulator with the app running
```

Edit `apps/counter/src/main.c` (or `src/lib.rs`) and save: the CLI rebuilds and the simulator restarts the app,
keeping its stored data. A failed build prints the error and leaves the last good one running. Close the window or
press Ctrl-C to stop.

The template is a counter: a title, the count, "+1" and "Reset" buttons, the count saved in the app's key-value
storage. `manifest.json` names the app and declares what it needs (`ui_mode` widgets or canvas, `memory_kb`,
`permissions`); docs/05 §3–§5 has every key and the API.

## 3. On the watch

```bash
s3w keygen                                    # once: ~/.s3w/dev.key signs your packages
s3w install apps/counter --usb --trust-key    # first time: the watch trusts your key (app key add)
s3w install apps/counter --usb                # later: the watch shows the install screen; tap Install
s3w logs                                      # your app's s3w_log lines
```

The app appears in the launcher under Mini apps (Games for `"category": "game"`); a long press uninstalls it.
Without a key, turn on the developer option "unsigned apps" (`settings set dev_unsigned 1` on the console).

## Rules worth knowing

- No libc: C apps are freestanding (`s3w.h` only), Rust apps are `no_std`. `s3w build` refuses a module that
  imports anything else.
- Callbacks return within 250 ms (only the app's own wasm time counts); three overruns, a hang in `s3w_on_start`, a trap
  or a panic stop the app. Aim far lower: a canvas frame at 30 fps has 33 ms.
- One thread: keep state in globals (`static mut` in Rust), touched only from the callbacks.
- Permissions are checked on every call: a function marked `[perm: x]` in `s3w.h` traps without `x` in the manifest.
- Icon: put an `icon.png` (80×80, round with transparent corners, 8-bit RGBA/RGB/grey/palette, not interlaced,
  ≤ 64 KB) next to `manifest.json`; `s3w build` packs it and the launcher shows it. Without one the launcher
  shows the name's first letter.
