# Input: touch, BOOT and gestures

## Widgets apps

Widgets deliver their own events: `S3W_EV_CLICK` for buttons and list rows, `S3W_EV_VALUE` for sliders and switches.
You do not see raw touches.

## Canvas apps

A canvas app gets touches in canvas pixels:

| Event | Fields |
|---|---|
| `S3W_EV_TOUCH_DOWN`, `S3W_EV_TOUCH_UP` | `x`, `y` |
| `S3W_EV_TOUCH_MOVE` | `x`, `y`, at most every 30 ms |
| `S3W_EV_TAP` | A short press (`x`, `y`) |
| `S3W_EV_LONG_PRESS` | Held without moving |
| `S3W_EV_SWIPE` | `value` is `S3W_DIR_LEFT`, `RIGHT`, `UP` or `DOWN` |

A swipe's release is not a tap. The screen's edges belong to the system (a swipe in from the left edge goes back), and
so do the PWR button (home) and, by default, BOOT.

```c-check
#include "s3w.h"

static int s_x = S3W_SCREEN_W / 2, s_y = S3W_SCREEN_H / 2;

static void draw(void)
{
    s3w_gfx_clear(S3W_RGB565(0, 0, 0));
    s3w_gfx_circle(s_x, s_y, 20, S3W_RGB565(255, 255, 255), true);
    s3w_gfx_present();
}

void s3w_on_start(void)
{
    draw();
}

void s3w_on_event(const s3w_event_t *e)
{
    switch (e->type) {
    case S3W_EV_TOUCH_DOWN:
    case S3W_EV_TOUCH_MOVE:
        s_x = e->x;
        s_y = e->y;
        break;
    case S3W_EV_SWIPE:
        s_x += e->value == S3W_DIR_LEFT ? -60 : e->value == S3W_DIR_RIGHT ? 60 : 0;
        s_y += e->value == S3W_DIR_UP ? -60 : e->value == S3W_DIR_DOWN ? 60 : 0;
        break;
    default:
        return;
    }
    draw();
}
```

## The BOOT button

If the manifest has `"capture_back": true`, the BOOT button is yours while your screen is up: you get
`S3W_EV_BUTTON` (`handle` is `S3W_BTN_BOOT`, `value` 1 pressed, 0 released) and the system does nothing with it. PWR still
goes home, so a game cannot lock the user in. The button returns to the system when your screen is covered, the display
goes off or the app ends. In the simulator, the script command `app-button down|up` presses it.

## Design for fingers

The screen is small: a target should be at least 48 px. Do not depend on a long hold for something users need, and give
a pressed state so a touch feels answered.
