# App lifecycle and callbacks

An app is a WebAssembly module. It **exports** the callbacks it wants (all optional) and **imports** the functions of
[the API](../api/index.md) from the module `s3w`. The watch calls your callbacks; you never run a loop of your own.

| Callback | When |
|---|---|
| `s3w_on_start` | Once, when the app opens. Build the UI, read saved state. 250 ms budget |
| `s3w_on_resume` | The app is visible again |
| `s3w_on_pause` | The app is covered, or the screen turned off |
| `s3w_on_stop` | The system ends the app. Not called after `s3w_exit`, a trap or a kill |
| `s3w_on_event` | One input, timer, sensor or network event |
| `s3w_on_frame` | Canvas apps only: every frame at the rate you asked for |

```c-check
#include "s3w.h"

static int s_starts;

void s3w_on_start(void)
{
    s_starts++;
    s3w_log(S3W_LOG_INFO, "started", 7);
}

void s3w_on_pause(void)
{
    /* the screen turned off or another screen covers the app: save what you would hate to lose */
    s3w_kv_set("starts", 6, &s_starts, sizeof s_starts);
}

void s3w_on_event(const s3w_event_t *e)
{
    if (e->type == S3W_EV_TIMER) {
        s3w_log(S3W_LOG_DEBUG, "tick", 4);
    }
}
```

## Events

`s3w_event_t` is 32 bytes: `type`, `handle`, `value`, `x`, `y`. The watch writes it into a buffer your module exports
(`s3w_event_buf`, defined by `s3w.h` and by the Rust crate for you) and calls `s3w_on_event`. The pointer is valid only
during the call: copy what you need. What the fields mean depends on `type`; the table is in
[constants and types](../api/constants.md).

## One app at a time

One app is in the foreground. It is suspended with its memory kept when the screen turns off, and destroyed if the user
leaves for more than a minute or memory is needed. Save anything you must keep with the
[storage](storage.md) functions, ideally on every change, not only in `s3w_on_pause`.

## One thread

There are no threads. Your callbacks are called one at a time from the same place, so plain global variables are safe
(Rust: `static mut`, touched only from the callbacks). Never wait in a callback: set a timer
([`s3w_timer_start`](../api/system.md#s3w_timer_start)) and handle `S3W_EV_TIMER`, or ask for a network answer and
handle `S3W_EV_HTTP`.

## Ending

`s3w_exit` ends the app at once. Leaving by the system's back gesture or the PWR button ends it through
`s3w_on_stop`. A trap or an overrun ends it with an error screen ([errors](../reference/errors.md)).
