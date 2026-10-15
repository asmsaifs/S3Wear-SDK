/* A planted timer leak: every tap starts a repeating timer and nothing stops it. */
#include "s3w.h"

void s3w_on_start(void)
{
    const int b = s3w_ui_button(s3w_ui_screen(), "tap", 3);
    s3w_ui_set_size(b, S3W_SIZE_FULL, S3W_SIZE_FULL);
}

void s3w_on_event(const s3w_event_t *e)
{
    if (e->type == S3W_EV_CLICK) {
        s3w_timer_start(1000, true); /* never stopped */
    }
}
