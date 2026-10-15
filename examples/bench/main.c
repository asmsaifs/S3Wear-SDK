/*
 * Canvas benchmark (api_level 1, canvas mode): the P8-03 performance test.
 *
 *   - 48 shaded ball sprites (4 colours = 4 frames of one sprite) bouncing at 60 fps requested
 *   - a spinning line (4 px wide) and a pulsing ring in the middle
 *   - the frame rate the app sees (frames per second of s3w_on_frame) at the top
 *
 * Every frame erases what moved, draws it at its new place and presents: only those areas go to
 * the display (dirty rectangles). The rate the display reaches is in the console (`app`).
 *
 * Freestanding C (no libc): build with sdk/examples/build.sh.
 */
#include "s3w.h"

#define BALLS     48
#define BALL      24                 /* sprite size, px */
#define KEY       0xF81F             /* magenta: transparent */
#define BG        S3W_RGB565(8, 12, 28)
#define HEADER_H  86                 /* the fps text lives above this */
#define TOP       (HEADER_H + 4)
#define BOTTOM    (S3W_SCREEN_H - 40) /* clear of the round corners */
#define LEFT      24
#define RIGHT     (S3W_SCREEN_W - 24)
#define CX        (S3W_SCREEN_W / 2)
#define CY        ((TOP + BOTTOM) / 2)
#define SPIN_R    70

#define STR(s) s, (int)(sizeof(s) - 1)

typedef struct {
    int x, y;   /* top left, 1/16 px */
    int vx, vy; /* 1/16 px per second */
    int color;  /* sprite frame */
} ball_t;

static uint16_t s_pixels[BALL * BALL * 4];
static ball_t s_balls[BALLS];
static int s_sprite;
static unsigned s_seed = 12345;
static int s_angle;       /* 0..31 */
static int s_spin_ms;
static int s_pulse_ms;
static int s_ring_r;
static int s_fps_frames;
static int s_fps_ms;
static int s_fps = -1;
static int s_fps_w;       /* width of the text drawn last */

/* sin(2 pi i / 32) x 1000 */
static const short k_sin[32] = {0,     195,  383,  556,  707,  831,  924,  981,  1000, 981,  924,
                                831,   707,  556,  383,  195,  0,    -195, -383, -556, -707, -831,
                                -924,  -981, -1000, -981, -924, -831, -707, -556, -383, -195};

static unsigned rnd(void)
{
    s_seed = s_seed * 1103515245u + 12345u;
    return s_seed >> 16;
}

static int fmt_int(char *buf, int n, const char *suffix)
{
    char digits[12];
    int d = 0;
    int len = 0;
    unsigned u = (unsigned)n;
    do {
        digits[d++] = (char)('0' + u % 10);
        u /= 10;
    } while (u);
    while (d) {
        buf[len++] = digits[--d];
    }
    while (*suffix) {
        buf[len++] = *suffix++;
    }
    return len;
}

/* A shaded ball per frame: brighter towards the top left, magenta outside. */
static void make_sprite(void)
{
    static const int base[4][3] = {{255, 90, 70}, {70, 200, 255}, {120, 230, 90}, {255, 200, 60}};
    for (int f = 0; f < 4; f++) {
        for (int y = 0; y < BALL; y++) {
            for (int x = 0; x < BALL; x++) {
                const int dx = 2 * x - (BALL - 1);
                const int dy = 2 * y - (BALL - 1);
                uint16_t c = KEY;
                if (dx * dx + dy * dy <= (BALL - 1) * (BALL - 1)) {
                    const int hx = 2 * x - BALL / 2;
                    const int hy = 2 * y - BALL / 2;
                    int light = 256 - (hx * hx + hy * hy) * 160 / (4 * BALL * BALL);
                    light = light < 64 ? 64 : light;
                    const int r = base[f][0] * light / 256;
                    const int g = base[f][1] * light / 256;
                    const int b = base[f][2] * light / 256;
                    c = S3W_RGB565(r, g, b);
                    if (c == KEY) {
                        c ^= 0x20; /* never the key colour */
                    }
                }
                s_pixels[(f * BALL + y) * BALL + x] = c;
            }
        }
    }
}

static void spinner(uint16_t color)
{
    const int x = CX + k_sin[(s_angle + 8) % 32] * SPIN_R / 1000;
    const int y = CY + k_sin[s_angle] * SPIN_R / 1000;
    s3w_gfx_line(CX, CY, x, y, color, 4);
}

static void show_fps(int fps)
{
    char t[16];
    const int n = fmt_int(t, fps, " fps");
    const int w = s3w_gfx_text_width(t, n, S3W_FONT_TITLE);
    const int wipe = w > s_fps_w ? w : s_fps_w;
    s3w_gfx_rect((S3W_SCREEN_W - wipe) / 2, 40, wipe, 40, BG, true);
    s3w_gfx_text((S3W_SCREEN_W - w) / 2, 40, t, n, S3W_FONT_TITLE, S3W_RGB565(255, 255, 255));
    s_fps_w = w;
}

void s3w_on_start(void)
{
    s3w_gfx_set_fps(S3W_GFX_FPS_MAX);
    make_sprite();
    s_sprite = s3w_gfx_sprite_create(s_pixels, BALL, BALL, 4, KEY);
    if (s_sprite < 0) {
        s3w_log(S3W_LOG_ERROR, STR("no sprite"));
        s3w_exit();
        return;
    }
    for (int i = 0; i < BALLS; i++) {
        ball_t *b = &s_balls[i];
        b->x = (LEFT + (int)(rnd() % (RIGHT - LEFT - BALL))) * 16;
        b->y = (TOP + (int)(rnd() % (BOTTOM - TOP - BALL))) * 16;
        b->vx = ((int)(rnd() % 160) + 60) * 16 * (rnd() & 1 ? 1 : -1);
        b->vy = ((int)(rnd() % 160) + 60) * 16 * (rnd() & 1 ? 1 : -1);
        b->color = i % 4;
    }
    s3w_gfx_clear(BG);
    const int tw = s3w_gfx_text_width(STR("Canvas bench"), S3W_FONT_CAPTION);
    s3w_gfx_text((S3W_SCREEN_W - tw) / 2, 8, STR("Canvas bench"), S3W_FONT_CAPTION, S3W_RGB565(150, 160, 190));
    s3w_gfx_line(LEFT, HEADER_H, RIGHT, HEADER_H, S3W_RGB565(40, 50, 80), 1);
    show_fps(0);
    s3w_gfx_present();
}

/* One coordinate of a ball: moves by v over dt, bouncing between lo and hi (1/16 px). */
static void bounce(int *p, int *v, int dt, int lo, int hi)
{
    *p += *v * dt / 1000;
    if (*p < lo) {
        *p = 2 * lo - *p;
        *v = -*v;
    } else if (*p > hi) {
        *p = 2 * hi - *p;
        *v = -*v;
    }
}

void s3w_on_frame(uint32_t dt_ms)
{
    const int dt = dt_ms > 100 ? 100 : (int)dt_ms;

    /* Erase: balls, spinner, ring. */
    for (int i = 0; i < BALLS; i++) {
        s3w_gfx_rect(s_balls[i].x / 16, s_balls[i].y / 16, BALL, BALL, BG, true);
    }
    spinner(BG);
    s3w_gfx_circle(CX, CY, s_ring_r, BG, false);

    /* Move. */
    for (int i = 0; i < BALLS; i++) {
        ball_t *b = &s_balls[i];
        bounce(&b->x, &b->vx, dt, LEFT * 16, (RIGHT - BALL) * 16);
        bounce(&b->y, &b->vy, dt, TOP * 16, (BOTTOM - BALL) * 16);
    }
    s_spin_ms += dt;
    s_angle = (s_angle + s_spin_ms / 40) % 32; /* a step every 40 ms */
    s_spin_ms %= 40;
    s_pulse_ms = (s_pulse_ms + dt) % 1200;
    s_ring_r = 20 + (s_pulse_ms < 600 ? s_pulse_ms : 1200 - s_pulse_ms) / 10;

    /* Draw: the ring and spinner under the balls. */
    s3w_gfx_circle(CX, CY, s_ring_r, S3W_RGB565(90, 110, 160), false);
    spinner(S3W_RGB565(230, 230, 240));
    for (int i = 0; i < BALLS; i++) {
        s3w_gfx_sprite(s_sprite, s_balls[i].x / 16, s_balls[i].y / 16, s_balls[i].color,
                       s_balls[i].vx < 0 ? S3W_SPRITE_FLIP_X : 0);
    }

    /* Frames per second over each full second (a frame with dt 0 starts the count). */
    s_fps_frames += dt_ms > 0;
    s_fps_ms += (int)dt_ms;
    if (s_fps_ms >= 1000) {
        const int fps = (s_fps_frames * 1000 + s_fps_ms / 2) / s_fps_ms;
        if (fps != s_fps) {
            s_fps = fps;
            show_fps(fps);
        }
        s_fps_frames = 0;
        s_fps_ms = 0;
    }
    s3w_gfx_present();
}
