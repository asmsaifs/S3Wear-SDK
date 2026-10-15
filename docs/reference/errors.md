# Errors and trap messages

## Return codes

Functions that return `int` give a value of 0 or more on success and a negative code on failure:

| Code | Name | Meaning |
|---|---|---|
| 0 | `S3W_OK` | Success |
| -1 | `S3W_ERR_INVALID` | An argument is out of range |
| -2 | `S3W_ERR_NO_RESOURCE` | A limit is reached (handles, timers, files, requests) |
| -3 | `S3W_ERR_NOT_FOUND` | No such key, file, asset |
| -4 | `S3W_ERR_UNSUPPORTED` | Not available on this watch or api_level |
| -5 | `S3W_ERR_NOT_READY` | The clock is not set, no phone is connected, nothing is loaded |
| -6 | `S3W_ERR_DENIED` | Refused: a host not in `http_hosts`, a path that is not the user's |
| -7 | `S3W_ERR_IO` | Storage failed |
| -8 | `S3W_ERR_NO_SPACE` | The app's storage quota is full |
| -9 | `S3W_ERR_TIMEOUT` | No answer in time (HTTP: 20 s) |
| -10 | `S3W_ERR_NETWORK` | The phone could not reach the server |

These are conditions your app should handle. A bug in the app, on the other hand, **stops the app**.

## What stops an app

The watch shows an error screen and the app ends. The simulator does the same, and `app-is trapped` (or `hung`) in a script
tells you which.

| Screen | Cause |
|---|---|
| App stopped | A trap: a memory access outside the module's memory, `unreachable`, a pointer or length argument outside the memory, a handle that is not live, a function of the other UI mode, a call without its permission (`s3w_fs_open: needs permission files`), a Rust panic |
| App not responding | A callback took over 250 ms three times, or `s3w_on_start` took over 250 ms once |

To find the cause, run `s3w logs` while the app runs on the watch, or watch the simulator's output. Typical fixes:
raise `memory_kb` (out-of-bounds from running out of memory), add the permission, check the handle you pass, or do less
in one callback.

## Why an install is refused

The watch checks a package before it installs it and says why when it refuses:

| Message | What to do |
|---|---|
| `not signed (developer option: unsigned apps)` | Sign with your key and trust it (`--trust-key`), or turn on "unsigned apps" |
| `signed by an unknown key` | `s3w install --trust-key`, or `app key add <hex>` |
| `signature does not match the package` | The package changed after signing: build and sign again |
| `signed differently from the installed version: uninstall it first` | An update must use the same key |
| `version X is installed (newer)` | Raise `version`; an update cannot be older |
| `manifest.json missing` / `over 8 KB` | The package needs one, at most 8 KB |
| `app.wasm missing` | The `entry` file is not in the package |
| `icon.png: not 80x80` and the like | See [icons](../guides/icons-and-screenshots.md) |
| `data/ is reserved` | Do not name a file under `data/` |
| `package over 4096 KB` / `more than 64 entries` | Make it smaller |
| `<id> is a preinstalled app` | Pick another id |
| `write failed (storage full?)` | Free space on the watch |

## Build errors

`s3w build` refuses a module that imports anything but `s3w.h` functions (for example a libc call left in a C app), a
manifest that lacks a required key, and an icon the watch could not decode. The compiler's own messages are shown as they
are.
