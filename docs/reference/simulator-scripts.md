# Simulator scripts

A script is a text file, one command per line; `#` starts a comment. The simulator runs it headless and exits non-zero if
a check fails:

```bash
s3w run-sim my-app --script test.txt --screenshot out.png     # for an app
s3w_sim --face my-face --script test.txt --screenshot out.png # for a face
```

**Determinism.** Headless runs use the time zone UTC and a pinned clock (10:09 on a fixed day). The UI's time moves only
with `wait`, `tap`, `hold` and `swipe`, in 5 ms steps, and touch and buttons come only from the script, so the same script
gives the same pixels. The boot screen fades for 500 ms before the first command.

## Input and time

| Command | Effect |
|---|---|
| `wait <ms>` | Let time pass: animations, timers, app frames |
| `tap <x> <y>` | Press 80 ms, release, settle 100 ms |
| `hold <x> <y> [ms]` | Press for ms (default 800: a long press), release |
| `touch down <x> <y>` / `touch move <x> <y>` / `touch up` | Keep the finger down; a screenshot in between shows the pressed state |
| `swipe <x1> <y1> <x2> <y2> [ms]` | Drag in a straight line (default 200 ms) |
| `key back\|power` | The hardware buttons: back, or home |
| `back` / `home` | Go back one screen / to the face |
| `time <HH:MM>` | Pin the clock to another time of the same day |
| `time unknown` | The "time not set" state |
| `shot <file.png>` | An extra screenshot in the middle of the script |

Coordinates are screen pixels: 410 wide, 502 high, origin top left. Wait at least 400 ms after a navigation and 300 ms
after an overlay appears before the script ends, or the screenshot catches an animation.

## Apps

| Command | Effect |
|---|---|
| `app <name\|id\|file.wasm>` | Run an app: a sample, an installed id or a module |
| `app-install <file.s3app>` | Check a package and show the install consent; a refused package toasts "App not installed" |
| `app-uninstall <id>` | Uninstall at once |
| `app-installed <id> <version\|none>` | Fail unless that version (or none) is installed |
| `app-stop` | The system stops the app (`s3w_on_stop` runs) |
| `app-is running\|exited\|trapped\|hung\|none` | Fail unless the current (or last) app is in that state |
| `app-frames <n>` | Fail unless the app has run n frames: canvas `s3w_on_frame` calls, or for a widgets app n frame periods of 1/30 s of run time |
| `imu <x> <y> <z>` | The acceleration apps read, in milli-g (default `0 0 1000`: lying flat) |
| `app-http <status> [body]\|error` | The phone's answer to the app's waiting HTTP request; `error` is a network error |
| `app-button down\|up` | The BOOT button, for an app with `"capture_back": true` |

`s3w run-sim` installs your app for you, so a script usually starts with `wait 600` instead of `app`.

## Faces

| Command | Effect |
|---|---|
| `face <id>` | Show a face by id |
| `face-json <file>` | Install a `face.json` (an installed face is replaced) |
| `face-is <id>` | Fail unless that face is active |
| `aod on\|off` | The always-on layout |
| `lit <max-%>` | Fail unless fewer than max percent of the pixels are lit (the AOD check) |
| `slot <face> <n> <comp\|default>` | Set a complication slot |
| `data demo\|clear` | The demo data complications show, or everything unknown |
| `demo <state> [on\|off]` | The demo-data switcher of `s3w face run-sim`: `low-battery` (12 %), `no-phone` (no phone battery, weather, next event or notification count), `12h` (a 12-hour clock), `aod` (the always-on layout), `no-data` (everything unknown). Without `on` or `off` it toggles. `demo reset` turns them all off |
| `face-images <n>` | Fail unless the watch's picture cache holds n decoded pictures (a face change frees the old face's) |

## Example

```
# a test of the counter app: three taps, then a picture
wait 600
tap 205 230
tap 205 230
tap 205 230
wait 300
app-is running
```

Exit status 0 means every check held. The simulator prints the reason for the first one that failed.
