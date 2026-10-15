/* A planted trap: the 12th tap reads outside the module's memory (the monkey test must find it). */
#include "s3w.h"

static int s_taps;

void s3w_on_start(void)
{
    const int b = s3w_ui_button(s3w_ui_screen(), "tap", 3);
    s3w_ui_set_size(b, S3W_SIZE_FULL, S3W_SIZE_FULL);
}

void s3w_on_event(const s3w_event_t *e)
{
    if (e->type == S3W_EV_CLICK && ++s_taps == 12) {
        *(volatile int *)0x7ffffff0 = 1;
    }
}
