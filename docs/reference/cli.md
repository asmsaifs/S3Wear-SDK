# The s3w command

```
s3w new <dir> [--lang c|rust] [--id ID] [--name NAME]     an app from a template
s3w build [dir] [--key K | --unsigned]                    build/app.wasm and build/<id>.s3app
s3w pack [dir] [--key K | --unsigned]                     only the package, from build/app.wasm
s3w sign <pkg> --key K                                    (re)sign a package
s3w keygen [K]                                            a developer key (default ~/.s3w/dev.key)
s3w key [K]                                               its public key, for `app key add` on the watch
s3w verify <pkg> [--pub HEX]                              check a package
s3w new <dir> --face [--id ID] [--name NAME]              a watch face from a template
s3w face build|pack|verify|run-sim ...                    watch faces (.s3face)
s3w sim install [--version V] | update | list             simulator binaries
s3w run-sim [dir] [--script F --screenshot F]             the simulator, reloaded on every change
s3w install [dir|pkg] --usb [--port P] [--yes] [--trust-key]   install on the watch over USB
s3w check [dir] [--developer LOGIN] [--out DIR] ...       the store's automated checks, on your machine
s3w logs [--port P] [--all]                               the watch's app log
```

A directory argument defaults to the current one. Packages are signed with `--key`, `$S3W_KEY` or `~/.s3w/dev.key` when
that exists, otherwise unsigned (`--unsigned` forces it).

## Building

`s3w build` compiles the app, then packs it. **C**: any clang with the wasm32 target (`$CLANG` picks one), freestanding
(`-Oz`, no libc); **Rust**: `cargo build --release --target wasm32-unknown-unknown`. Both build for the processor the watch's
runtime has (no reference types, bulk memory on). Linear memory is the manifest's `memory_kb`; the stack is 8 KB. After the
build the module's imports are checked: anything that is not an `s3w.h` function (a libc call left over, say) is refused.

## Simulator

`s3w run-sim` builds an unsigned package and starts the simulator with it installed (without the consent screen); a change to
`manifest.json`, `src/`, `assets/` or `Cargo.toml` rebuilds and reinstalls it, keeping the app's data. A failed build keeps
the last good one. With `--script` or `--screenshot` it runs headless and exits. The simulator comes from `--sim`,
`$S3W_SIM`, a checkout's `build/sim`, or the newest one `s3w sim install` put in `~/.s3w/sim`.

## Installing

`s3w install <dir|pkg> --usb` builds, signs and uploads over the watch's USB console (about 1.5 KB/s), then runs
`app install` on the watch; the watch asks you to confirm unless `--yes`. `--trust-key` first adds your signing key to the
watch's trusted keys. `s3w logs` streams the log lines of apps; `--all` shows everything the watch logs.

## Faces

`s3w new <dir> --face` makes a face from a template (a vector face with the time, date, a battery ring, steps and a
complication); `--id` and `--name` as for apps.

`s3w face build <dir>` checks `face.json` with the simulator's parser and every picture (valid PNG, size limits), renders
`build/preview.png` and packs `build/<id>.s3face`; `pack` packs with the preview of the last build; `verify <pkg>` checks a
package without the simulator. Options: `--out`, `--sim`, `--key` or `--unsigned`.

`s3w face run-sim <dir>` shows the face in the simulator and reloads it whenever `face.json` or a picture is saved; a face
the parser refuses is reported with its line and column and the window keeps the last good one. Keys in the window
switch demo data: **B** low battery, **P** no phone, **H** 12-hour clock, **A** always-on layout, **N** no data, **R**
reset. With `--script` or `--screenshot` it runs headless once; `--no-watch` turns the reloading off.

## Checking before you submit

`s3w check [dir]` runs the store's automated checks on an app or a face folder, with the same code as the store's job. It
needs the simulator for the run checks (a check it cannot run is reported as skipped), and a C or Rust toolchain for the
build.

```bash
s3w check apps/io.github.you.snake --developer you --out report
```

| Option | Meaning |
|---|---|
| `--developer LOGIN` | Your login in the store repository: turns on the ownership check (the id must be in your namespaces) and the `developer` field of `listing.json` |
| `--profile FILE` | Your developer profile (`developers/<login>.json`), for domain namespaces |
| `--changed FILE` | The paths a pull request changes, one per line: changes to another developer's files are refused |
| `--published INDEX` | The published store index: the version must be higher |
| `--out DIR` | Write `report.json`, `report.md` and the screenshots there |
| `--monkey-seconds N`, `--seed N` | Length (default 120 simulated seconds) and seed of the random-input test; the same seed repeats the run |
| `--verify-dns` | Check the DNS TXT record of a domain namespace (needs `dig`) |
| `--blocklist FILE` | More names to keep out of listings (JSON: `trademarks`, `brands`, `offensive`) |
| `--only a,b`, `--no-run` | Run just those checks / skip the simulator runs |
| `--print-schema` | Print the JSON Schema of `listing.json` |

The exit status is 0 when nothing failed. Errors fail the submission; warnings go to the reviewer. See
[the review guidelines](../publish/review-guidelines.md) for what each check means.

## Environment

| Variable | Effect |
|---|---|
| `S3W_KEY` | The signing key file |
| `CLANG` | The clang for C builds |
| `S3W_SIM` | The simulator binary |
| `S3W_HOME` | Replaces `~/.s3w` for the simulators |
| `S3W_SIM_URL` | The site `s3w sim` downloads from (https or file://) |
| `S3W_SDK` | A different SDK directory (headers, templates, crates) |

Exit status is 0 on success and 1 on any error, with the reason on stderr.
