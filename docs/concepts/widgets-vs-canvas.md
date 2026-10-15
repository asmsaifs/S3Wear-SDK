# Widgets and canvas

The manifest's `ui_mode` picks one of two ways to put something on the screen. The mode is fixed for the app;
calling a function of the other mode stops the app (except `s3w_ui_toast` and `s3w_ui_dialog`, which work in both).

| | Widgets | Canvas |
|---|---|---|
| You build | A tree of labels, buttons, lists, sliders, switches | Nothing: you draw lines, rectangles, text, sprites |
| The watch does | Layout, scrolling, touch, drawing | Only flushing the pixels you drew |
| Input | `S3W_EV_CLICK`, `S3W_EV_VALUE` from widgets | Touch down/move/up, tap, long press, swipe, IMU |
| Updates | When you change a widget | Every frame in `s3w_on_frame` |
| Good for | Tools: calculators, lists, settings, timers | Games, animations, custom gauges |
| Cost when idle | Nothing | A frame callback at your fps; the watch runs faster while a canvas app is in front |

Use widgets unless you need to draw. A widgets app costs less battery, scrolls and looks like the watch's own
screens, and the watch handles rounded corners and touch for you.

## Widgets

You get a full-screen black container from `s3w_ui_screen()` and add children. Place them with a flex layout
(`S3W_STYLE_FLEX`) or by alignment and position (`S3W_STYLE_ALIGN`, `s3w_ui_set_pos`). See [widgets](../guides/widgets.md).

## Canvas

You get a 410 × 502 RGB565 canvas that keeps its pixels. Draw what changed, then call `s3w_gfx_present()` once; only the
areas drawn since the last present reach the display. See [canvas drawing](../guides/canvas.md).

The display has rounded corners: keep text about 24 px in from the edges.
