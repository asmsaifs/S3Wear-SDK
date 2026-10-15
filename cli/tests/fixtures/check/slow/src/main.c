/* Every tap spends tens of milliseconds in the app's own code: over the 50 ms the check warns about, under the 250 ms
 * limit (the loop is counted, not timed: the simulator's s3w_millis stands still inside a call). */
#include "s3w.h"

#define SPIN 2600000u
static volatile unsigned s_sink;

void s3w_on_start(void)
{
    const int b = s3w_ui_button(s3w_ui_screen(), "tap", 3);
    s3w_ui_set_size(b, S3W_SIZE_FULL, S3W_SIZE_FULL);
}

void s3w_on_event(const s3w_event_t *e)
{
    if (e->type == S3W_EV_CLICK) {
        for (unsigned i = 0; i < SPIN; i++) {
            s_sink++;
        }
    }
}
