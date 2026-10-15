# Limits and the watchdog

| Limit | Value |
|---|---|
| Linear memory | The manifest's `memory_kb`: 64 to 1024, default 256 (whole 64 KB pages). Stack 8 KB |
| Package | At most 4 MB, 64 files; `manifest.json` at most 8 KB; `icon.png` at most 64 KB |
| UI handles | 512 |
| Timers | 8 at once, at least 20 ms |
| Open files | 4 (app storage), 1 (device files) |
| Sprites | 64, together at most 512 KB of pixels |
| HTTP | 2 requests at once, 4 KB request body, 64 KB response, 20 s |
| Notifications | One every 10 s |
| Touch move events | At most every 30 ms |
| Frame rate | 1 to 60, default 30 |

## The watchdog

Every call into your app has a time limit, measured as wall time spent in **your** code (time the watch spends
drawing or building widgets for you does not count):

- `s3w_on_start`: 250 ms. A hang here kills the app at once.
- Every other callback: it must return within 250 ms, but aim far lower. A 30 fps canvas has 33 ms per frame in all, and
  the watch is slower than the simulator.
- Three overruns kill the app with "App not responding".

A trap also ends the app: an out-of-bounds memory access, `unreachable`, a pointer argument outside your memory, a call
without its permission, a widget handle that is not live, or a function of the other UI mode. The simulator shows the
same error screens, so test there.

## Memory

Static data, the stack and the heap of your language all live in the one linear memory. C apps are freestanding:
there is no `malloc`; use static arrays. Rust apps are `no_std` without an allocator unless you provide one. If
`memory_kb` is too small the module fails to load; raise it by 64 and rebuild.

## Battery

The watch runs faster while a canvas app is in front and counts each app's time in the foreground in the Battery
settings. Stop animating when nothing changes, draw only what changed, and lower the frame rate for slow things.
