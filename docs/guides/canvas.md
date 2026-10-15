# Canvas drawing and sprites

A canvas app has one 410 × 502 RGB565 surface that **keeps its pixels between frames** and starts black. You draw
what changed, then call `s3w_gfx_present()` once. Only the rectangles you drew since the last present are sent to the
display, so a small change is cheap and a still screen costs nothing.

| Draw | Function |
|---|---|
| Clear | `s3w_gfx_clear(color)` |
| Rectangle, circle | `s3w_gfx_rect(x, y, w, h, color, fill)`, `s3w_gfx_circle(cx, cy, r, color, fill)` |
| Line | `s3w_gfx_line(x0, y0, x1, y1, color, width)`, width 1 to 16 |
| Text | `s3w_gfx_text(x, y, text, len, font, color)` and `s3w_gfx_text_width` to centre |
| Pixels | `s3w_gfx_blit(pixels, x, y, w, h)` from app memory |
| Sprites | `s3w_gfx_sprite_create`, then `s3w_gfx_sprite(id, x, y, frame, flags)` |

Colours are RGB565: `S3W_RGB565(r, g, b)`. Everything clips to the canvas.

## Sprites

A sprite is a strip of frames of RGB565 pixels, stacked top to bottom, copied into the watch once. Drawing one is
cheaper than blitting it, and it can be flipped and can have a transparent key colour.

```c-check
#include "s3w.h"

#define W 16
#define H 16
#define KEY S3W_RGB565(255, 0, 255)

static uint16_t s_pixels[W * H * 2]; /* two frames, one below the other */
static int s_sprite;
static int s_x, s_dir = 4, s_frame;

static void make_frames(void)
{
    for (int f = 0; f < 2; f++) {
        for (int y = 0; y < H; y++) {
            for (int x = 0; x < W; x++) {
                const int dx = x - W / 2, dy = y - H / 2;
                const int r = f ? 7 : 5;
                s_pixels[f * W * H + y * W + x] = dx * dx + dy * dy <= r * r ? S3W_RGB565(0, 229, 255) : KEY;
            }
        }
    }
}

void s3w_on_start(void)
{
    make_frames();
    s_sprite = s3w_gfx_sprite_create(s_pixels, W, H, 2, KEY);
    s3w_gfx_set_fps(30);
}

void s3w_on_frame(uint32_t dt_ms)
{
    (void)dt_ms;
    /* erase the old box, draw the new one: the dirty rectangle is just those two boxes */
    s3w_gfx_rect(s_x, 200, W, H, S3W_RGB565(0, 0, 0), true);
    s_x += s_dir;
    if (s_x < 0 || s_x > S3W_SCREEN_W - W) {
        s_dir = -s_dir;
        s_x += s_dir;
    }
    s_frame ^= 1;
    s3w_gfx_sprite(s_sprite, s_x, 200, s_frame, s_dir < 0 ? S3W_SPRITE_FLIP_X : 0);
    s3w_gfx_present();
}
```

Limits: 64 sprites and 512 KB of sprite pixels per app; a frame index out of range or an unknown sprite id stops the app.
Pixel pointers must be 2-byte aligned. `s3w_gfx_sprite_load` (from the package's assets) returns
`S3W_ERR_NOT_FOUND` for now: build sprites in code, or embed the pixels as arrays.

## Frames

`s3w_gfx_set_fps(fps)` asks for 1 to 60 frames a second (default 30). `s3w_on_frame(dt_ms)` receives the time since
the previous frame (0 for the first one after start or resume): move things by `speed * dt_ms`, not by a fixed amount, and
the game runs the same at any rate. A frame that is late by a period or more is dropped, not queued. There are no frames
while the app is paused.

## Making it fast

- **Erase and redraw only what moves.** Clearing the whole canvas every frame sends the whole screen to the display; a
  small sprite moving sends two small boxes.
- **Draw text once**, when the value changes, not every frame.
- **Prefer integers.** Integer maths is cheaper in the interpreter; measure before you rely on floats.
- **Measure on the watch**: it is slower than the simulator. [Performance](performance.md) has numbers.
