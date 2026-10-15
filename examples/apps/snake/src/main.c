/*
 * Snake (preinstalled game, canvas): steer with swipes, or by tilting the watch (past 15°, the
 * stronger axis wins); eat the red dots to grow and speed up; hitting the wall or yourself ends the
 * game. Score = 10 per dot, best on high-score board 0.
 *
 * Drawing: each step redraws three cells at most (new head, old head as body, the tail cleared);
 * the score line only when it changes.
 */
#include "../../common/game_util.h"

#define CELL   18
#define COLS   20
#define ROWS   21
#define AX     ((G_W - COLS * CELL) / 2)
#define AY     82
#define MAXLEN (COLS * ROWS)
#define STEP_START_MS 160
#define STEP_MIN_MS   70
#define TILT_DEG      15.0f

#define C_FIELD S3W_RGB565(0x10, 0x14, 0x10)
#define C_EDGE  S3W_RGB565(0x3A, 0x3A, 0x3C)
#define C_BODY  S3W_RGB565(0x2E, 0xA0, 0x4A)
#define C_HEAD  S3W_RGB565(0x6E, 0xE0, 0x80)
#define C_FOOD  S3W_RGB565(0xFF, 0x45, 0x3A)

enum { TITLE, PLAY, OVER };

static struct {
    int mode;
    uint8_t x[MAXLEN], y[MAXLEN]; /* ring buffer, head at (head) */
    int head, len, grow;
    uint8_t occ[ROWS][COLS];
    int dx, dy;
    int queue[2], queued; /* turns waiting for the next steps */
    int fx, fy;
    int score, best, new_best;
    uint32_t acc_ms, step_ms;
    int score_dirty, full;
} s;

static void cell(int cx, int cy, uint16_t c)
{
    s3w_gfx_rect(AX + cx * CELL, AY + cy * CELL, CELL, CELL, C_FIELD, true);
    if (c != C_FIELD) {
        s3w_gfx_rect(AX + cx * CELL + 1, AY + cy * CELL + 1, CELL - 2, CELL - 2, c, true);
    }
}

static void food_cell(void)
{
    s3w_gfx_rect(AX + s.fx * CELL, AY + s.fy * CELL, CELL, CELL, C_FIELD, true);
    s3w_gfx_circle(AX + s.fx * CELL + CELL / 2, AY + s.fy * CELL + CELL / 2, CELL / 2 - 2, C_FOOD, true);
}

static void place_food(void)
{
    const int free_ = COLS * ROWS - s.len;
    if (free_ <= 0) {
        s.fx = -1;
        return;
    }
    int k = s3w_random() % free_;
    for (int y = 0; y < ROWS; y++) {
        for (int x = 0; x < COLS; x++) {
            if (!s.occ[y][x] && k-- == 0) {
                s.fx = x;
                s.fy = y;
                food_cell();
                return;
            }
        }
    }
}

static void draw_score(void)
{
    g_band(20, 56, G_BLACK);
    char t[40];
    int n = u_cat_int(t, 0, s.score);
    n = u_cat(t, n, "   \xC2\xB7   Best ");
    n = u_cat_int(t, n, s.best > s.score ? s.best : s.score);
    g_text_at(G_CX, 34, t, n, S3W_FONT_BODY, G_WHITE);
    s.score_dirty = 0;
}

static void start(void)
{
    for (int y = 0; y < ROWS; y++) {
        for (int x = 0; x < COLS; x++) {
            s.occ[y][x] = 0;
        }
    }
    s.len = 4;
    s.head = s.len - 1;
    for (int i = 0; i < s.len; i++) {
        s.x[i] = (uint8_t)(4 + i);
        s.y[i] = ROWS / 2;
        s.occ[ROWS / 2][4 + i] = 1;
    }
    s.dx = 1;
    s.dy = 0;
    s.queued = 0;
    s.grow = 0;
    s.score = 0;
    s.new_best = 0;
    s.step_ms = STEP_START_MS;
    s.acc_ms = 0;
    s.mode = PLAY;
    s3w_gfx_clear(G_BLACK);
    s3w_gfx_rect(AX - 3, AY - 3, COLS * CELL + 6, ROWS * CELL + 6, C_EDGE, true);
    s3w_gfx_rect(AX, AY, COLS * CELL, ROWS * CELL, C_FIELD, true);
    for (int i = 0; i < s.len; i++) {
        cell(s.x[i], s.y[i], i == s.head ? C_HEAD : C_BODY);
    }
    place_food();
    s.score_dirty = 1;
}

static void turn(int dx, int dy)
{
    /* Compared with the last queued direction: no reversing, no repeats. */
    int ldx = s.dx, ldy = s.dy;
    if (s.queued) {
        ldx = s.queue[s.queued - 1] >> 8;
        ldy = (int8_t)(s.queue[s.queued - 1] & 0xFF);
    }
    if ((dx == -ldx && dy == -ldy) || (dx == ldx && dy == ldy) || s.queued == 2) {
        return;
    }
    s.queue[s.queued++] = (dx << 8) | (dy & 0xFF);
}

static void die(void)
{
    s.mode = OVER;
    s.new_best = s3w_highscore_submit(0, s.score) == 1 && s.score > 0;
    s.best = g_best(0);
    s3w_audio_tone(147, 500, 70);
    g_over("Game over", "Score ", s.score, "Best ", s.best, s.new_best);
}

static void step(void)
{
    if (s.queued) {
        s.dx = s.queue[0] >> 8;
        s.dy = (int8_t)(s.queue[0] & 0xFF);
        s.queue[0] = s.queue[1];
        s.queued--;
    }
    const int hx = s.x[s.head] + s.dx, hy = s.y[s.head] + s.dy;
    const int tail = (s.head - s.len + 1 + MAXLEN) % MAXLEN;
    const int eats = hx == s.fx && hy == s.fy;
    if (hx < 0 || hx >= COLS || hy < 0 || hy >= ROWS) {
        die();
        return;
    }
    /* Moving into the tail's cell is fine unless the tail stays (growing). */
    if (s.occ[hy][hx] && !(hx == s.x[tail] && hy == s.y[tail] && !s.grow)) {
        die();
        return;
    }
    cell(s.x[s.head], s.y[s.head], C_BODY);
    if (s.grow) {
        s.grow--;
        s.len++;
    } else {
        s.occ[s.y[tail]][s.x[tail]] = 0;
        if (!(hx == s.x[tail] && hy == s.y[tail])) {
            cell(s.x[tail], s.y[tail], C_FIELD);
        }
    }
    s.head = (s.head + 1) % MAXLEN;
    s.x[s.head] = (uint8_t)hx;
    s.y[s.head] = (uint8_t)hy;
    s.occ[hy][hx] = 1;
    cell(hx, hy, C_HEAD);
    if (eats) {
        s.score += 10;
        s.grow += 2;
        s.step_ms = s.step_ms > STEP_MIN_MS + 4 ? s.step_ms - 4 : STEP_MIN_MS;
        s.score_dirty = 1;
        s3w_audio_tone(880, 40, 50);
        place_food();
    }
}

static void tilt_steer(void)
{
    float pitch, roll;
    if (s3w_tilt(&pitch, &roll) != S3W_OK) {
        return;
    }
    if (u_absf(roll) >= u_absf(pitch) && u_absf(roll) > TILT_DEG) {
        turn(roll > 0 ? 1 : -1, 0); /* 3 o'clock down: right */
    } else if (u_absf(pitch) > TILT_DEG) {
        turn(0, pitch > 0 ? -1 : 1); /* 12 o'clock raised: up */
    }
}

static void title(void)
{
    s.mode = TITLE;
    g_title("Snake", "Best ", s.best, s.best > 0, "Tap to start", G_BLACK);
    /* A curled snake as art. */
    static const int8_t k_art[][2] = {{0, 0}, {1, 0}, {2, 0}, {3, 0}, {3, 1}, {3, 2}, {2, 2}, {1, 2}, {1, 3},
                                      {1, 4}, {2, 4}, {3, 4}, {4, 4}, {5, 4}};
    const int n = (int)(sizeof k_art / sizeof k_art[0]);
    for (int i = 0; i < n; i++) {
        const int x = 140 + k_art[i][0] * 22, y = 170 + k_art[i][1] * 22;
        s3w_gfx_rect(x, y, 20, 20, i == n - 1 ? C_HEAD : C_BODY, true);
    }
    s3w_gfx_circle(140 + 7 * 22 + 10, 170 + 4 * 22 + 10, 8, C_FOOD, true);
    g_text(446, "Swipe or tilt to steer", S3W_FONT_CAPTION, G_DIM);
}

void s3w_on_start(void)
{
    s3w_keep_screen_on(true); /* screen stays on while playing; released when the app closes */
    s.best = g_best(0);
    s3w_gfx_set_fps(30);
    title();
}

void s3w_on_frame(uint32_t dt_ms)
{
    if (s.mode == PLAY) {
        tilt_steer();
        s.acc_ms += dt_ms;
        while (s.mode == PLAY && s.acc_ms >= s.step_ms) {
            s.acc_ms -= s.step_ms;
            step();
        }
        if (s.score_dirty && s.mode == PLAY) {
            draw_score();
        }
    }
    s3w_gfx_present();
}

void s3w_on_event(const s3w_event_t *e)
{
    if (e->type == S3W_EV_TAP && s.mode != PLAY && g_may_restart()) {
        start();
    } else if (e->type == S3W_EV_SWIPE && s.mode == PLAY) {
        switch (e->value) {
        case S3W_DIR_LEFT: turn(-1, 0); break;
        case S3W_DIR_RIGHT: turn(1, 0); break;
        case S3W_DIR_UP: turn(0, -1); break;
        default: turn(0, 1); break;
        }
    }
}
