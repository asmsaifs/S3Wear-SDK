/*
 * Widgets sample (api_level 1): every widget, a timer and the clock.
 *
 *   - the time at the top (s3w_time_local)
 *   - a ring and its value in the middle, set by the slider or by "+10"
 *   - a switch that starts a 1 s timer counting the seconds at the bottom
 *
 * Freestanding C (no libc): build with sdk/examples/build.sh.
 */
#include "s3w.h"

#define STR(s) s, (int)(sizeof(s) - 1)

static int s_ring, s_value_label, s_plus, s_slider, s_switch, s_elapsed;
static int s_timer;
static int s_value = 40;
static int s_seconds;

/* "<prefix><n><suffix>" into buf; returns the length. */
static int fmt_int(char *buf, const char *prefix, int n, const char *suffix)
{
    int len = 0;
    while (*prefix) {
        buf[len++] = *prefix++;
    }
    char digits[12];
    int d = 0;
    unsigned u = n < 0 ? (unsigned)-n : (unsigned)n;
    do {
        digits[d++] = (char)('0' + u % 10);
        u /= 10;
    } while (u);
    if (n < 0) {
        buf[len++] = '-';
    }
    while (d) {
        buf[len++] = digits[--d];
    }
    while (*suffix) {
        buf[len++] = *suffix++;
    }
    return len;
}

static void show_value(void)
{
    char t[16];
    s3w_ui_set_value(s_ring, s_value);
    s3w_ui_set_value(s_slider, s_value);
    s3w_ui_set_text(s_value_label, t, fmt_int(t, "", s_value, "%"));
}

static void show_elapsed(void)
{
    char t[32];
    s3w_ui_set_text(s_elapsed, t, fmt_int(t, "Elapsed ", s_seconds, " s"));
}

static int place(int h, int align, int x, int y)
{
    s3w_ui_set_style(h, S3W_STYLE_ALIGN, align);
    s3w_ui_set_pos(h, x, y);
    return h;
}

void s3w_on_start(void)
{
    const int scr = s3w_ui_screen();

    s3w_tm_t tm;
    char t[8] = "--:--";
    if (s3w_time_local(&tm) == S3W_OK) {
        t[0] = (char)('0' + tm.hour / 10);
        t[1] = (char)('0' + tm.hour % 10);
        t[3] = (char)('0' + tm.minute / 10);
        t[4] = (char)('0' + tm.minute % 10);
    }
    const int clock = place(s3w_ui_label(scr, t, 5), S3W_ALIGN_TOP_MID, 0, 14);
    s3w_ui_set_style(clock, S3W_STYLE_FONT, S3W_FONT_CAPTION);
    s3w_ui_set_style(clock, S3W_STYLE_TEXT_COLOR, 0x9A9AA0);

    const int title = place(s3w_ui_label(scr, STR("Widgets")), S3W_ALIGN_TOP_MID, 0, 44);
    s3w_ui_set_style(title, S3W_STYLE_FONT, S3W_FONT_TITLE);

    s_ring = place(s3w_ui_arc(scr, 0, 100, s_value), S3W_ALIGN_TOP_MID, 0, 96);
    s_value_label = place(s3w_ui_label(scr, STR("")), S3W_ALIGN_TOP_MID, 0, 158);
    s3w_ui_set_style(s_value_label, S3W_STYLE_FONT, S3W_FONT_TITLE);

    s_plus = place(s3w_ui_button(scr, STR("+10")), S3W_ALIGN_TOP_MID, 0, 272);
    s_slider = place(s3w_ui_slider(scr, 0, 100, s_value), S3W_ALIGN_TOP_MID, 0, 362);

    place(s3w_ui_label(scr, STR("Timer")), S3W_ALIGN_TOP_MID, -60, 402);
    s_switch = place(s3w_ui_switch(scr, false), S3W_ALIGN_TOP_MID, 70, 400);

    s_elapsed = place(s3w_ui_label(scr, STR("")), S3W_ALIGN_TOP_MID, 0, 448);
    s3w_ui_set_style(s_elapsed, S3W_STYLE_FONT, S3W_FONT_CAPTION);
    s3w_ui_set_style(s_elapsed, S3W_STYLE_TEXT_COLOR, 0x9A9AA0);

    show_value();
    show_elapsed();
    s3w_log(S3W_LOG_INFO, STR("widgets sample started"));
}

void s3w_on_event(const s3w_event_t *e)
{
    if (e->type == S3W_EV_CLICK && e->handle == s_plus) {
        s_value = s_value >= 100 ? 0 : s_value + 10;
        show_value();
    } else if (e->type == S3W_EV_VALUE && e->handle == s_slider) {
        s_value = e->value;
        show_value();
    } else if (e->type == S3W_EV_VALUE && e->handle == s_switch) {
        if (e->value && !s_timer) {
            s_timer = s3w_timer_start(1000, true);
            s3w_ui_toast(STR("Timer on"));
        } else if (!e->value && s_timer) {
            s3w_timer_stop(s_timer);
            s_timer = 0;
        }
    } else if (e->type == S3W_EV_TIMER && e->handle == s_timer) {
        s_seconds++;
        show_elapsed();
    }
}
