/* A planted leak: every tap makes a label and never deletes it (s3w check's monkey test must catch it). */
#include "s3w.h"

static int s_screen, s_n;

void s3w_on_start(void)
{
    s_screen = s3w_ui_screen();
    const int b = s3w_ui_button(s_screen, "tap", 3);
    s3w_ui_set_size(b, S3W_SIZE_FULL, S3W_SIZE_FULL);
}

void s3w_on_event(const s3w_event_t *e)
{
    if (e->type == S3W_EV_CLICK) {
        s3w_ui_label(s_screen, "x", 1); /* never deleted */
        s_n++;
    }
}
