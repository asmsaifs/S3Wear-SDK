/*
 * Breakout (preinstalled game, canvas): move the paddle by dragging (or by tilting while the screen
 * is not touched), tap to launch, clear the bricks. Three balls; each cleared wall comes back
 * faster. Higher rows score more. Best on high-score board 0.
 *
 * Drawing per frame: the ball's and the paddle's old boxes cleared and redrawn; a hit brick erased;
 * the score line when it changes.
 */
#include "../../common/game_util.h"

#define BCOLS   7
#define BROWS   6
#define BRICK_W 48
#define BRICK_H 18
#define BGAP    4
#define BRX     ((G_W - BCOLS * BRICK_W - (BCOLS - 1) * BGAP) / 2)
#define BRY     96
#define TOP     78
#define LEFT    14
#define RIGHT   (G_W - 14)
#define PAD_Y   432
#define PAD_W   84
#define PAD_H   12
#define BALL_R  7
#define SPEED0  260.0f
#define TILT_GAIN 14.0f /* px/s per degree */
#define TILT_DEAD 3.0f  /* degrees around the pose held at the start */

#define C_BG    G_BLACK
#define C_PAD   S3W_RGB565(0xE0, 0xE0, 0xE6)
#define C_BALL  S3W_RGB565(0xFF, 0xFF, 0xFF)
#define C_EDGE  S3W_RGB565(0x2C, 0x2C, 0x2E)

static const uint16_t k_row_color[BROWS] = {
    S3W_RGB565(0xFF, 0x45, 0x3A), S3W_RGB565(0xFF, 0x9F, 0x0A), S3W_RGB565(0xFF, 0xD6, 0x0A),
    S3W_RGB565(0x30, 0xD1, 0x58), S3W_RGB565(0x40, 0xC8, 0xE0), S3W_RGB565(0x3D, 0x8B, 0xFF),
};

enum { TITLE, SERVE, PLAY, OVER };

static struct {
    int mode;
    uint8_t brick[BROWS][BCOLS];
    int bricks_left;
    float bx, by, vx, vy, speed;
    float pad_x; /* centre */
    int drawn_bx, drawn_by, drawn_pad;
    int touching;
    float tilt_zero; /* roll held at the start = level */
    int tilt_zeroed;
    int score, lives, wall, best, new_best;
    int hud_dirty;
} s;

static void brick_rect(int r, int c, int *x, int *y)
{
    *x = BRX + c * (BRICK_W + BGAP);
    *y = BRY + r * (BRICK_H + BGAP);
}

static void draw_bricks(void)
{
    for (int r = 0; r < BROWS; r++) {
        for (int c = 0; c < BCOLS; c++) {
            if (s.brick[r][c]) {
                int x, y;
                brick_rect(r, c, &x, &y);
                s3w_gfx_rect(x, y, BRICK_W, BRICK_H, k_row_color[r], true);
            }
        }
    }
}

static void draw_hud(void)
{
    g_band(20, TOP - 24, C_BG);
    char t[40];
    int n = u_cat_int(t, 0, s.score);
    n = u_cat(t, n, "   ");
    for (int i = 0; i < s.lives; i++) {
        n = u_cat(t, n, "\xE2\x80\xA2"); /* bullet per ball left */
    }
    g_text_at(G_CX, 30, t, n, S3W_FONT_BODY, G_WHITE);
    s.hud_dirty = 0;
}

static void draw_paddle(void)
{
    const int x = (int)s.pad_x - PAD_W / 2;
    if (x == s.drawn_pad) {
        return;
    }
    if (s.drawn_pad > -1000) {
        s3w_gfx_rect(s.drawn_pad, PAD_Y, PAD_W, PAD_H, C_BG, true);
    }
    g_rrect(x, PAD_Y, PAD_W, PAD_H, PAD_H / 2, C_PAD);
    s.drawn_pad = x;
}

static void draw_ball(void)
{
    const int x = (int)s.bx, y = (int)s.by;
    if (x == s.drawn_bx && y == s.drawn_by) {
        return;
    }
    if (s.drawn_bx > -1000) {
        s3w_gfx_rect(s.drawn_bx - BALL_R, s.drawn_by - BALL_R, 2 * BALL_R + 1, 2 * BALL_R + 1, C_BG, true);
    }
    s3w_gfx_circle(x, y, BALL_R, C_BALL, true);
    s.drawn_bx = x;
    s.drawn_by = y;
}

static void new_wall(void)
{
    for (int r = 0; r < BROWS; r++) {
        for (int c = 0; c < BCOLS; c++) {
            s.brick[r][c] = 1;
        }
    }
    s.bricks_left = BROWS * BCOLS;
    draw_bricks();
}

static void serve(void)
{
    s.mode = SERVE;
    s.bx = s.pad_x;
    s.by = PAD_Y - BALL_R - 1;
}

static void start(void)
{
    s3w_gfx_clear(C_BG);
    s3w_gfx_rect(LEFT - 4, TOP - 4, 4, PAD_Y + 40 - TOP, C_EDGE, true);
    s3w_gfx_rect(RIGHT, TOP - 4, 4, PAD_Y + 40 - TOP, C_EDGE, true);
    s3w_gfx_rect(LEFT - 4, TOP - 4, RIGHT - LEFT + 8, 4, C_EDGE, true);
    s.score = 0;
    s.lives = 3;
    s.wall = 0;
    s.new_best = 0;
    s.speed = SPEED0;
    s.pad_x = G_CX;
    s.drawn_bx = s.drawn_pad = -10000;
    s.tilt_zeroed = 0;
    new_wall();
    s.hud_dirty = 1;
    serve();
}

static void launch(void)
{
    s.mode = PLAY;
    s.vx = s.speed * 0.6f;
    s.vy = -s.speed * 0.8f;
}

static void game_over(void)
{
    s.mode = OVER;
    s.new_best = s3w_highscore_submit(0, s.score) == 1 && s.score > 0;
    s.best = g_best(0);
    s3w_audio_tone(131, 500, 70);
    g_over(s.bricks_left ? "Game over" : "Cleared!", "Score ", s.score, "Best ", s.best, s.new_best);
}

static void set_speed(float sp)
{
    const float cur = __builtin_sqrtf(s.vx * s.vx + s.vy * s.vy);
    if (cur > 0) {
        s.vx *= sp / cur;
        s.vy *= sp / cur;
    }
}

/* The first brick the ball's box overlaps: bounce on the axis of least overlap, erase it. */
static void hit_bricks(void)
{
    const int bx0 = (int)s.bx - BALL_R, by0 = (int)s.by - BALL_R, bx1 = bx0 + 2 * BALL_R, by1 = by0 + 2 * BALL_R;
    if (by0 > BRY + BROWS * (BRICK_H + BGAP) || by1 < BRY) {
        return;
    }
    for (int r = 0; r < BROWS; r++) {
        for (int c = 0; c < BCOLS; c++) {
            if (!s.brick[r][c]) {
                continue;
            }
            int x, y;
            brick_rect(r, c, &x, &y);
            if (bx1 < x || bx0 > x + BRICK_W || by1 < y || by0 > y + BRICK_H) {
                continue;
            }
            const int ox = (bx1 < x + BRICK_W ? bx1 - x : x + BRICK_W - bx0);
            const int oy = (by1 < y + BRICK_H ? by1 - y : y + BRICK_H - by0);
            if (ox < oy) {
                s.vx = -s.vx;
            } else {
                s.vy = -s.vy;
            }
            s.brick[r][c] = 0;
            s.bricks_left--;
            s3w_gfx_rect(x, y, BRICK_W, BRICK_H, C_BG, true);
            s.score += (BROWS - r) * 10;
            s.hud_dirty = 1;
            s3w_audio_tone(440 + (BROWS - r) * 80, 30, 40);
            return;
        }
    }
}

static void title(void)
{
    s.mode = TITLE;
    g_title("Breakout", "Best ", s.best, s.best > 0, "Tap to start", C_BG);
    for (int r = 0; r < 4; r++) {
        for (int c = 0; c < 5; c++) {
            s3w_gfx_rect(95 + c * 46, 150 + r * 22, 42, 18, k_row_color[r], true);
        }
    }
    s3w_gfx_circle(230, 300, BALL_R, C_BALL, true);
    g_rrect(163, 340, PAD_W, PAD_H, PAD_H / 2, C_PAD);
    g_text(446, "Drag or tilt the paddle", S3W_FONT_CAPTION, G_DIM);
}

void s3w_on_start(void)
{
    s3w_keep_screen_on(true); /* screen stays on while playing; released when the app closes */
    s.best = g_best(0);
    float pitch, roll;
    s3w_tilt(&pitch, &roll); /* starts the accelerometer, so the start pose is a settled sample */
    s3w_gfx_set_fps(30);
    title();
}

void s3w_on_frame(uint32_t dt_ms)
{
    if (s.mode == SERVE || s.mode == PLAY) {
        if (dt_ms > 50) {
            dt_ms = 50;
        }
        const float dt = (float)dt_ms / 1000.0f;
        /* Tilt relative to the pose at the start (a wrist is rarely level). */
        float pitch, roll;
        if (s3w_tilt(&pitch, &roll) == S3W_OK) {
            if (!s.tilt_zeroed) {
                s.tilt_zero = roll;
                s.tilt_zeroed = 1;
            }
            roll -= s.tilt_zero;
        } else {
            roll = 0.0f;
        }
        if (!s.touching && u_absf(roll) > TILT_DEAD) {
            roll += roll > 0.0f ? -TILT_DEAD : TILT_DEAD;
            s.pad_x -= roll * TILT_GAIN * dt * 2.0f; /* downhill: a raised 3 o'clock moves it left */
        }
        const float lo = LEFT + PAD_W / 2, hi = RIGHT - PAD_W / 2;
        s.pad_x = s.pad_x < lo ? lo : s.pad_x > hi ? hi : s.pad_x;
        if (s.mode == SERVE) {
            s.bx = s.pad_x;
        } else {
            const int steps = 1 + (int)(s.speed * dt / 6);
            for (int i = 0; i < steps && s.mode == PLAY; i++) {
                s.bx += s.vx * dt / steps;
                s.by += s.vy * dt / steps;
                if (s.bx < LEFT + BALL_R) {
                    s.bx = LEFT + BALL_R;
                    s.vx = u_absf(s.vx);
                } else if (s.bx > RIGHT - BALL_R) {
                    s.bx = RIGHT - BALL_R;
                    s.vx = -u_absf(s.vx);
                }
                if (s.by < TOP + BALL_R) {
                    s.by = TOP + BALL_R;
                    s.vy = u_absf(s.vy);
                }
                /* Paddle: the angle depends on where it hits. */
                if (s.vy > 0 && s.by + BALL_R >= PAD_Y && s.by + BALL_R <= PAD_Y + PAD_H + 6 &&
                    u_absf(s.bx - s.pad_x) <= PAD_W / 2 + BALL_R) {
                    const float k = (s.bx - s.pad_x) / (PAD_W / 2 + BALL_R); /* -1..1 */
                    s.vx = s.speed * k * 0.85f;
                    s.vy = -__builtin_sqrtf(s.speed * s.speed - s.vx * s.vx);
                    s.by = PAD_Y - BALL_R;
                    s3w_audio_tone(330, 20, 30);
                }
                hit_bricks();
                if (s.bricks_left == 0) {
                    s.wall++;
                    s.speed += 40;
                    set_speed(s.speed);
                    new_wall();
                }
                if (s.by > PAD_Y + 40) {
                    s.lives--;
                    s.hud_dirty = 1;
                    s3w_audio_tone(196, 200, 60);
                    if (s.lives == 0) {
                        draw_hud();
                        game_over();
                        s3w_gfx_present();
                        return;
                    }
                    serve();
                }
            }
        }
        draw_paddle();
        draw_ball();
        if (s.hud_dirty) {
            draw_hud();
        }
    }
    s3w_gfx_present();
}

void s3w_on_event(const s3w_event_t *e)
{
    switch (e->type) {
    case S3W_EV_TAP:
        if (s.mode == TITLE || (s.mode == OVER && g_may_restart())) {
            start();
        } else if (s.mode == SERVE) {
            launch();
        }
        break;
    case S3W_EV_TOUCH_DOWN:
    case S3W_EV_TOUCH_MOVE:
        s.touching = 1;
        if (s.mode == SERVE || s.mode == PLAY) {
            s.pad_x = (float)e->x;
        }
        break;
    case S3W_EV_TOUCH_UP:
        s.touching = 0;
        break;
    default:
        break;
    }
}
