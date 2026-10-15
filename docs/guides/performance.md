# Performance on the real watch

The simulator runs your WebAssembly on a PC; the watch runs it in an interpreter on a 240 MHz processor. Expect it to be
much slower, and measure on the watch before you decide a game is smooth.

## Budgets

| What | Budget |
|---|---|
| Any callback | 250 ms hard limit (the watchdog) |
| A 30 fps frame | 33 ms for everything: your code, the drawing, the flush |
| A 60 fps frame | 16 ms |
| `s3w_on_start` | 250 ms, then the screen shows |

Measured on a watch, the firmware's own games reach the rate they ask for: a tap-to-fly game 59.9 fps of the 60 it asks
for, a breakout game 29.9 and a space shooter 29.4 of 30 (that one spends about 6 ms a frame drawing 15 areas). The games
that change something every frame spend their time drawing, not in game logic; the ones that draw only on a change cost
almost nothing.

## What helps

- **Draw less.** Erase and redraw only the boxes that moved (see [canvas drawing](canvas.md)); text once per change.
- **Prefer integers.** Integer maths is cheaper and more predictable in an interpreter; measure before you rely on floats.
- **Avoid per-frame work you can precompute**: tables, sprite frames, strings.
- **Lower the frame rate** for slow things. 15 fps is plenty for a clock; no frame callback at all for a widgets app.
- **Keep the module small.** `-Oz`, no libc, no formatting libraries; the template's `fmt_int` is 15 lines. A small
  `.wasm` loads fast and fits a small `memory_kb`.
- **Be careful with big loops in callbacks**: a loop that is fast on a PC can take most of 250 ms on the watch.

## Memory

Pick `memory_kb` just above what you use; the watch holds it in PSRAM while the app runs, and a smaller number leaves
room for the system. Static arrays count; the stack is 8 KB.

## Check your size

`s3w build` prints the package size. Small apps install quickly: over USB the upload runs at about 1.5 KB/s, so a
100 KB app takes about a minute.
