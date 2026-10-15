# Overview

S3Wear is a smartwatch with a 410 × 502 round-cornered AMOLED display, a touch screen, an accelerometer and two
buttons (BOOT and PWR). You can add to it in two ways:

| | Mini app | Watch face |
|---|---|---|
| What it is | A WebAssembly module (C or Rust) in a sandbox | A `face.json` file and optional images |
| Runs code | Yes, your code, on the watch | No: it only names values the watch already has |
| Examples | A counter, a calculator, a game | A dial, a neon digital clock |
| Start with | [Your first app](first-app-c.md) | [Your first watch face](first-face.md) |

## What runs where

- **Your PC**: the `s3w` command-line tool builds, packs, signs and installs; the desktop **simulator** runs the
  watch's own UI code, so an app behaves in it as it does on the watch. A build takes a second or two.
- **The watch**: runs your app in a sandbox (the WAMR WebAssembly runtime). The app can call only the functions in
  [the API reference](../api/index.md); anything else is refused when you build and again when it is installed.
- **The phone**: the S3Wear Companion app installs apps and faces from the store, and shows the install consent.

## What you need

- **A watch with the Pro firmware.** Mini apps and installable faces are Pro features; the Community edition does not
  run third-party apps. Without a Pro licence the watch runs the Pro features for a 14-day trial, which is enough to
  try everything here. You do not need a watch to start: the simulator runs everything below.
- A computer with macOS or Linux (Windows: WSL2). Python 3.9 or newer, and a C compiler that targets WebAssembly or
  Rust. [Install the SDK](install.md) shows the commands, or use the [dev container](install.md#the-dev-container)
  and install nothing.

## How the pieces fit

1. Write the app: a `manifest.json` (name, permissions) and C or Rust source against one header, `s3w.h`.
2. `s3w run-sim` builds it and shows it in the simulator; every save rebuilds and reloads it.
3. `s3w install --usb` puts it on your watch, signed with your own key.
4. When it is ready, [publish it](../publish/index.md) to the store.

Read [the concepts](../concepts/lifecycle.md) once before you write a bigger app: the rules about callbacks, time
limits and permissions are short, and breaking one stops the app.
