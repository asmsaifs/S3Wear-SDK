/*
 * {{name}}: a counter that survives restarts (the S3Wear C template, api_level 1).
 *
 *   s3w build .     -> build/app.wasm and build/{{id}}.s3app
 *   s3w run-sim .   -> the simulator, rebuilt and reloaded on every save
 *
 * Freestanding C: no libc (s3w.h is the whole API). Callbacks must return within
 * 250 ms. The developer docs have the API and the rules.
 */
#include "s3w.h"

#define STR(s) s, (int)(sizeof(s) - 1)

static int s_count_label, s_plus, s_reset;
static int s_count;

/* n in decimal into buf (at least 12 bytes); returns the length. */
static int fmt_int(char *buf, int n)
{
    char d[12];
    int k = 0, len = 0;
    unsigned u = n < 0 ? (unsigned)-n : (unsigned)n;
    do {
        d[k++] = (char)('0' + u % 10);
        u /= 10;
    } while (u);
    if (n < 0) {
        buf[len++] = '-';
    }
    while (k) {
        buf[len++] = d[--k];
    }
    return len;
}

static void show(void)
{
    char t[12];
    s3w_ui_set_text(s_count_label, t, fmt_int(t, s_count));
}

static void save(void)
{
    s3w_kv_set(STR("count"), &s_count, sizeof s_count); /* app-private storage */
}

void s3w_on_start(void)
{
    s3w_log(S3W_LOG_INFO, STR("{{name}} started"));
    if (s3w_kv_get(STR("count"), &s_count, sizeof s_count) != (int)sizeof s_count) {
        s_count = 0;
    }
    const int scr = s3w_ui_screen();
    s3w_ui_set_style(scr, S3W_STYLE_FLEX, S3W_FLEX_COLUMN);
    s3w_ui_set_style(scr, S3W_STYLE_PAD, 40);
    s3w_ui_set_style(scr, S3W_STYLE_GAP, 16);

    const int title = s3w_ui_label(scr, STR("{{name}}"));
    s3w_ui_set_style(title, S3W_STYLE_FONT, S3W_FONT_TITLE);
    s_count_label = s3w_ui_label(scr, STR("0"));
    s3w_ui_set_style(s_count_label, S3W_STYLE_FONT, S3W_FONT_DISPLAY);
    s_plus = s3w_ui_button(scr, STR("+1"));
    s3w_ui_set_size(s_plus, 200, S3W_SIZE_CONTENT);
    s_reset = s3w_ui_button(scr, STR("Reset"));
    s3w_ui_set_size(s_reset, 200, S3W_SIZE_CONTENT);
    show();
}

void s3w_on_event(const s3w_event_t *e)
{
    if (e->type != S3W_EV_CLICK) {
        return;
    }
    if (e->handle == s_plus) {
        s_count++;
    } else if (e->handle == s_reset) {
        s_count = 0;
    }
    show();
    save();
}
