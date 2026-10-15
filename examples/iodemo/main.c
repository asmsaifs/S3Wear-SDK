/*
 * I/O sample (api_level 1, canvas mode): the P8-04 bindings on one screen.
 *
 *   - tilt the watch: the ball rolls (S3W_EV_IMU at 50 Hz)          [imu]
 *   - tap: a click tone, a dot where you tapped, the count is kept   [audio.play; storage]
 *   - long press: a notification with the count                      [notify]
 *   - swipe up: GET https://httpbin.org/get through the phone        [phone.http]
 *   - swipe down: forget the count
 *
 * The watch grants these permissions to the built-in `iodemo` until packages carry a manifest.
 * Freestanding C (no libc): build with sdk/examples/build.sh.
 */
#include "s3w.h"

#define STR(s) s, (int)(sizeof(s) - 1)

#define BG      S3W_RGB565(10, 14, 24)
#define FG      S3W_RGB565(235, 235, 245)
#define DIM     S3W_RGB565(140, 150, 175)
#define BALL_C  S3W_RGB565(90, 200, 255)
#define DOT_C   S3W_RGB565(255, 170, 60)
#define BALL_R  16
#define TOP     110 /* the ball's field */
#define BOTTOM  380
#define LEFT    40
#define RIGHT   (S3W_SCREEN_W - 40)
#define LINE_Y  396 /* status line */

static int s_taps;
static int s_bx = S3W_SCREEN_W / 2, s_by = (TOP + BOTTOM) / 2; /* ball, px */
static int s_drawn_x = -1, s_drawn_y;
static int s_ax, s_ay;     /* latest acceleration, mg */
static bool s_imu;         /* events arrive */
static int s_http_id;
static char s_resp[512];
static char s_line[48];
static int s_line_len;
static bool s_dirty_text = true;

static int fmt(char *buf, const char *a, int n, const char *b)
{
    int len = 0;
    while (*a) {
        buf[len++] = *a++;
    }
    char d[12];
    int k = 0;
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
    while (*b) {
        buf[len++] = *b++;
    }
    return len;
}

static void status(const char *a, int n, const char *b)
{
    s_line_len = fmt(s_line, a, n, b);
    s_dirty_text = true;
}

static void save_taps(void)
{
    char v[12];
    s3w_kv_set(STR("taps"), v, fmt(v, "", s_taps, ""));
}

static void draw_text(void)
{
    char t[24];
    s3w_gfx_rect(0, 56, S3W_SCREEN_W, 40, BG, true);
    const int n = fmt(t, "", s_taps, s_taps == 1 ? " tap" : " taps");
    const int w = s3w_gfx_text_width(t, n, S3W_FONT_TITLE);
    s3w_gfx_text((S3W_SCREEN_W - w) / 2, 56, t, n, S3W_FONT_TITLE, FG);
    s3w_gfx_rect(0, LINE_Y, S3W_SCREEN_W, 34, BG, true);
    const int lw = s3w_gfx_text_width(s_line, s_line_len, S3W_FONT_CAPTION);
    s3w_gfx_text((S3W_SCREEN_W - lw) / 2, LINE_Y, s_line, s_line_len, S3W_FONT_CAPTION, DIM);
    s_dirty_text = false;
}

void s3w_on_start(void)
{
    char v[12];
    const int n = s3w_kv_get(STR("taps"), v, sizeof v);
    for (int i = 0; i < n && i < (int)sizeof v; i++) {
        s_taps = s_taps * 10 + (v[i] - '0');
    }
    s3w_keep_screen_on(true);
    const int hz = s3w_imu_start(50);
    s_imu = hz > 0;
    if (s_imu) {
        status("Tilt me (", hz, " Hz)");
    } else {
        status("No IMU (", hz, ")");
    }
    s3w_gfx_clear(BG);
    const int tw = s3w_gfx_text_width(STR("I/O demo"), S3W_FONT_CAPTION);
    s3w_gfx_text((S3W_SCREEN_W - tw) / 2, 16, STR("I/O demo"), S3W_FONT_CAPTION, DIM);
    s3w_gfx_rect(LEFT - 4, TOP - 4, RIGHT - LEFT + 8, BOTTOM - TOP + 8, S3W_RGB565(50, 60, 90), false);
    const int hw = s3w_gfx_text_width(STR("tap, hold, swipe up or down"), S3W_FONT_CAPTION);
    s3w_gfx_text((S3W_SCREEN_W - hw) / 2, 436, STR("tap, hold, swipe up or down"), S3W_FONT_CAPTION, DIM);
    s3w_gfx_present();
}

void s3w_on_event(const s3w_event_t *e)
{
    switch (e->type) {
    case S3W_EV_IMU:
        s_ax = e->x;
        s_ay = e->y;
        break;
    case S3W_EV_TAP:
        s_taps++;
        save_taps();
        s3w_audio_tone(1200, 40, 60);
        s3w_gfx_circle(e->x, e->y, 5, DOT_C, true);
        status("Tap at ", e->x, "");
        break;
    case S3W_EV_LONG_PRESS: {
        char body[24];
        const int r = s3w_notify(STR("I/O demo"), body, fmt(body, "Taps so far: ", s_taps, ""));
        status("Notification: ", r, r == 0 ? " (sent)" : "");
        break;
    }
    case S3W_EV_SWIPE:
        if (e->value == S3W_DIR_UP && !s_http_id) {
            static s3w_http_req_t req; /* filled field by field: no memcpy without libc */
            req.method = S3W_HTTP_GET;
            req.url = "https://httpbin.org/get?from=s3wear";
            req.url_len = 35;
            req.resp = s_resp;
            req.resp_cap = sizeof s_resp;
            const int id = s3w_http_request(&req);
            if (id > 0) {
                s_http_id = id;
                status("HTTP request ", id, " sent");
            } else {
                status("HTTP failed: ", id, "");
            }
        } else if (e->value == S3W_DIR_DOWN) {
            s_taps = 0;
            s3w_kv_delete(STR("taps"));
            s3w_gfx_rect(LEFT, TOP, RIGHT - LEFT, BOTTOM - TOP, BG, true);
            s_drawn_x = -1;
            status("Count cleared", 0, "");
            s_line_len -= 1; /* drop the "0" */
        }
        break;
    case S3W_EV_HTTP:
        if (e->handle == s_http_id) {
            s_http_id = 0;
            if (e->value > 0) {
                char t[48];
                const int n = fmt(t, "HTTP ", e->value, ", ");
                s_line_len = n + fmt(t + n, "", e->x, e->y ? "+ bytes" : " bytes");
                for (int i = 0; i < s_line_len; i++) {
                    s_line[i] = t[i];
                }
                s_dirty_text = true;
            } else {
                status("HTTP error ", e->value, "");
            }
        }
        break;
    default:
        break;
    }
}

void s3w_on_frame(uint32_t dt_ms)
{
    /* The ball rolls downhill: acceleration in mg moves it (screen y grows down, the watch's
     * +y is 12 o'clock). */
    const int dt = dt_ms > 100 ? 100 : (int)dt_ms;
    s_bx += s_ax * dt / 1500;
    s_by -= s_ay * dt / 1500;
    s_bx = s_bx < LEFT + BALL_R ? LEFT + BALL_R : s_bx > RIGHT - BALL_R ? RIGHT - BALL_R : s_bx;
    s_by = s_by < TOP + BALL_R ? TOP + BALL_R : s_by > BOTTOM - BALL_R ? BOTTOM - BALL_R : s_by;
    if (s_bx != s_drawn_x || s_by != s_drawn_y) {
        if (s_drawn_x >= 0) {
            s3w_gfx_circle(s_drawn_x, s_drawn_y, BALL_R, BG, true);
        }
        s3w_gfx_circle(s_bx, s_by, BALL_R, BALL_C, true);
        s_drawn_x = s_bx;
        s_drawn_y = s_by;
    }
    if (s_dirty_text) {
        draw_text();
    }
    s3w_gfx_present();
}
