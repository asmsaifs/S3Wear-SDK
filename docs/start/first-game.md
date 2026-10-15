# Your first game

A game draws its own pixels: the manifest says `"ui_mode": "canvas"` and the app gets a 410 × 502 canvas in RGB565
colour that keeps its pixels between frames. This one is a ball that falls; you tap to kick it up and keep it in the
air. It uses a frame callback, touch input, drawing, and the high-score service.

```bash
s3w new bounce --id dev.you.bounce --name "Bounce"
# replace bounce/src/main.c with the code below, and in bounce/manifest.json set
#   "ui_mode": "canvas" and "category": "game"
s3w run-sim bounce
```

![Bounce: the ball in the air with the score](../img/bounce.png)

## The code

```c-check project=first-game
#include "s3w.h"

#define STR(s) s, (int)(sizeof(s) - 1)

#define BALL_R 22
#define GRAVITY 1800 /* px per second squared */
#define KICK (-720)  /* px per second, up */

static int s_x = S3W_SCREEN_W / 2;
static int s_y = 100;
static int s_vy;       /* px per second */
static int s_score;
static int s_best;
static bool s_over;

static int fmt_int(char *buf, int n)
{
    char d[12];
    int k = 0, len = 0;
    unsigned u = (unsigned)n;
    do {
        d[k++] = (char)('0' + u % 10);
        u /= 10;
    } while (u);
    while (k) {
        buf[len++] = d[--k];
    }
    return len;
}

static void new_game(void)
{
    s_y = 100;
    s_vy = 0;
    s_score = 0;
    s_over = false;
}

static void draw(void)
{
    char t[12];
    s3w_gfx_clear(S3W_RGB565(0, 0, 0));
    s3w_gfx_circle(s_x, s_y, BALL_R, S3W_RGB565(255, 214, 10), true);
    s3w_gfx_line(0, S3W_SCREEN_H - 3, S3W_SCREEN_W, S3W_SCREEN_H - 3, S3W_RGB565(90, 90, 96), 4);
    const int n = fmt_int(t, s_score);
    s3w_gfx_text((S3W_SCREEN_W - s3w_gfx_text_width(t, n, S3W_FONT_DISPLAY)) / 2, 40, t, n, S3W_FONT_DISPLAY,
                 S3W_RGB565(255, 255, 255));
    if (s_over) {
        const int w = s3w_gfx_text_width(STR("Tap to retry"), S3W_FONT_TITLE);
        s3w_gfx_text((S3W_SCREEN_W - w) / 2, 250, STR("Tap to retry"), S3W_FONT_TITLE, S3W_RGB565(255, 69, 58));
        int best = 0;
        if (s3w_highscore_get(0, &best) == S3W_OK) {
            s_best = best;
        }
        const int m = fmt_int(t, s_best);
        s3w_gfx_text(40, 300, STR("Best"), S3W_FONT_BODY, S3W_RGB565(154, 154, 160));
        s3w_gfx_text(140, 300, t, m, S3W_FONT_BODY, S3W_RGB565(154, 154, 160));
    }
    s3w_gfx_present();
}

void s3w_on_start(void)
{
    s3w_gfx_set_fps(30);
    new_game();
    draw();
}

void s3w_on_frame(uint32_t dt_ms)
{
    if (!s_over) {
        s_vy += (int)(GRAVITY * dt_ms / 1000);
        s_y += s_vy * (int)dt_ms / 1000;
        if (s_y + BALL_R >= S3W_SCREEN_H - 4) {
            s_over = true;
            s3w_highscore_submit(0, s_score);
        }
    }
    draw();
}

void s3w_on_event(const s3w_event_t *e)
{
    if (e->type != S3W_EV_TAP) {
        return;
    }
    if (s_over) {
        new_game();
    } else {
        s_vy = KICK;
        s_score++;
    }
}
```

## How it works

- **`s3w_on_frame(dt_ms)`** is called at the rate you set with [`s3w_gfx_set_fps`](../api/canvas-mode.md#s3w_gfx_set_fps)
  while the app is visible. `dt_ms` is the time since the last frame, so the motion is the same at 30 or 60 fps.
  Everything the game does in a frame must finish in a few milliseconds; the [limits](../concepts/limits.md) page has
  the budget.
- **Drawing** is cheap when little changes: the canvas keeps its pixels and only the areas drawn since the last
  [`s3w_gfx_present`](../api/canvas-mode.md#s3w_gfx_present) are sent to the display. This game clears and redraws
  everything for simplicity; a bigger game erases and redraws just the parts that move (see
  [canvas drawing](../guides/canvas.md)).
- **Input** arrives in `s3w_on_event`. `S3W_EV_TAP` is a short press; touch down, move and up and swipes are there
  too ([input](../guides/input.md)).
- **Colours** are RGB565: `S3W_RGB565(r, g, b)` packs three 8-bit values.
- **The score** is kept by [`s3w_highscore_submit`](../api/game-services.md#s3w_highscore_submit), which stores the best
  value of a board in the app's storage, so it survives restarts and updates.

## Ideas

Add a sound with `s3w_audio_tone` (needs the `audio.play` [permission](../concepts/permissions.md)), tilt control
with `s3w_tilt` (`imu`), or make the ball speed up as the score grows.
