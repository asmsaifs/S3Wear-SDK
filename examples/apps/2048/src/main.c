/*
 * 2048 (preinstalled game, canvas): swipe to slide every tile; equal tiles merge and add to the
 * score. A new 2 (or 4) appears after each move, growing in over a few frames. No move left: game
 * over, with the best score (high-score board 0). The board is saved after every move (kv "board"),
 * so a game goes on after the app closes.
 *
 * Drawing: only tiles whose value changed (or that are growing) are redrawn.
 */
#include "../../common/game_util.h"

#define N      4
#define TILE   82
#define GAP    8
#define BOARD  (N * TILE + (N + 1) * GAP)
#define BX     ((G_W - BOARD) / 2)
#define BY     104
#define POP_FRAMES 4

#define C_BOARD S3W_RGB565(0x3A, 0x3A, 0x3C)
#define C_EMPTY S3W_RGB565(0x4A, 0x4A, 0x4E)

static struct {
    struct {
        int32_t cell[N * N]; /* 0 or 2, 4, 8, ... */
        int32_t score;
        int32_t over;
        int32_t won;         /* 2048 reached (shown once) */
    } st;
    int32_t shown[N * N];   /* value drawn, -1 = redraw */
    int pop_cell, pop_frame; /* the new tile growing in */
    int best;
    int header_dirty, full;
    int new_best;
} s;

static uint16_t tile_color(int v)
{
    switch (v) {
    case 2: return S3W_RGB565(0xEE, 0xE4, 0xDA);
    case 4: return S3W_RGB565(0xED, 0xE0, 0xC8);
    case 8: return S3W_RGB565(0xF2, 0xB1, 0x79);
    case 16: return S3W_RGB565(0xF5, 0x95, 0x63);
    case 32: return S3W_RGB565(0xF6, 0x7C, 0x5F);
    case 64: return S3W_RGB565(0xF6, 0x5E, 0x3B);
    case 128: return S3W_RGB565(0xED, 0xCF, 0x72);
    case 256: return S3W_RGB565(0xED, 0xCC, 0x61);
    case 512: return S3W_RGB565(0xED, 0xC8, 0x50);
    case 1024: return S3W_RGB565(0xED, 0xC5, 0x3F);
    case 2048: return S3W_RGB565(0xED, 0xC2, 0x2E);
    default: return v ? S3W_RGB565(0x3C, 0x3A, 0x32) : C_EMPTY;
    }
}

static void draw_tile(int i, int scale_pct)
{
    const int x = BX + GAP + (i % N) * (TILE + GAP);
    const int y = BY + GAP + (i / N) * (TILE + GAP);
    const int v = s.st.cell[i];
    s3w_gfx_rect(x, y, TILE, TILE, C_BOARD, true);
    const int sz = TILE * scale_pct / 100;
    const int off = (TILE - sz) / 2;
    g_rrect(x + off, y + off, sz, sz, 10 * scale_pct / 100 + 2, tile_color(v));
    if (v && scale_pct == 100) {
        char t[8];
        const int n = u_cat_int(t, 0, v);
        const int font = v < 1000 ? S3W_FONT_TITLE : S3W_FONT_BODY;
        const uint16_t c = v <= 4 ? S3W_RGB565(0x77, 0x6E, 0x65) : G_WHITE;
        g_text_at(x + TILE / 2, y + TILE / 2 - (font == S3W_FONT_TITLE ? 20 : 16), t, n, font, c);
    }
}

static void draw_header(void)
{
    g_band(14, 84, G_BLACK);
    char t[32];
    int n = u_cat_int(t, 0, s.st.score);
    g_text_at(G_CX, 20, t, n, S3W_FONT_TITLE, G_WHITE);
    if (s.st.won == 1) {
        g_text(62, "2048! Keep going", S3W_FONT_CAPTION, G_YELLOW);
    } else {
        n = u_cat(t, 0, "Best ");
        n = u_cat_int(t, n, s.best > s.st.score ? s.best : s.st.score);
        g_text_at(G_CX, 62, t, n, S3W_FONT_CAPTION, G_DIM);
    }
    s.header_dirty = 0;
}

static void save(void)
{
    s3w_kv_set(STR("board"), &s.st, sizeof s.st);
}

static int empty_cells(int *out)
{
    int n = 0;
    for (int i = 0; i < N * N; i++) {
        if (!s.st.cell[i]) {
            out[n++] = i;
        }
    }
    return n;
}

static void spawn(void)
{
    int free_[N * N];
    const int n = empty_cells(free_);
    if (n == 0) {
        return;
    }
    const int i = free_[s3w_random() % n];
    s.st.cell[i] = s3w_random() % 10 == 0 ? 4 : 2;
    s.pop_cell = i;
    s.pop_frame = 1;
}

static void new_game(void)
{
    for (int i = 0; i < N * N; i++) {
        s.st.cell[i] = 0;
    }
    s.st.score = 0;
    s.st.over = 0;
    s.st.won = 0;
    s.new_best = 0;
    spawn();
    s.pop_frame = 0;
    spawn();
    s.full = 1;
    save();
}

/* Cell index of position k (0 = the edge the tiles slide to) on line l, for a direction. */
static int at(int dir, int l, int k)
{
    switch (dir) {
    case S3W_DIR_LEFT: return l * N + k;
    case S3W_DIR_RIGHT: return l * N + (N - 1 - k);
    case S3W_DIR_UP: return k * N + l;
    default: return (N - 1 - k) * N + l; /* down */
    }
}

/* Slides every line; returns whether anything moved. */
static int slide(int dir, int *gained, int *merges)
{
    int moved = 0;
    for (int l = 0; l < N; l++) {
        int line[N], out[N] = {0, 0, 0, 0}, n = 0, o = 0;
        for (int k = 0; k < N; k++) {
            const int v = s.st.cell[at(dir, l, k)];
            if (v) {
                line[n++] = v;
            }
        }
        for (int k = 0; k < n; k++) {
            if (k + 1 < n && line[k] == line[k + 1]) {
                out[o++] = line[k] * 2;
                *gained += line[k] * 2;
                (*merges)++;
                k++;
            } else {
                out[o++] = line[k];
            }
        }
        for (int k = 0; k < N; k++) {
            int *c = &s.st.cell[at(dir, l, k)];
            if (*c != out[k]) {
                *c = out[k];
                moved = 1;
            }
        }
    }
    return moved;
}

static int can_move(void)
{
    for (int i = 0; i < N * N; i++) {
        const int v = s.st.cell[i];
        if (!v || (i % N < N - 1 && s.st.cell[i + 1] == v) || (i / N < N - 1 && s.st.cell[i + N] == v)) {
            return 1;
        }
    }
    return 0;
}

static void game_over(void)
{
    s.st.over = 1;
    s.new_best = s3w_highscore_submit(0, s.st.score) == 1 && s.st.score > 0;
    s.best = g_best(0);
    save();
    s3w_audio_tone(196, 400, 60);
}

void s3w_on_start(void)
{
    s3w_keep_screen_on(true); /* screen stays on while playing; released when the app closes */
    s.best = g_best(0);
    s.pop_cell = -1;
    if (s3w_kv_get(STR("board"), &s.st, sizeof s.st) != (int)sizeof s.st || s.st.over) {
        new_game();
    }
    s.full = 1;
    s3w_gfx_set_fps(30);
}

void s3w_on_frame(uint32_t dt_ms)
{
    (void)dt_ms;
    if (s.full) {
        s3w_gfx_clear(G_BLACK);
        g_rrect(BX, BY, BOARD, BOARD, 14, C_BOARD);
        for (int i = 0; i < N * N; i++) {
            s.shown[i] = -1;
        }
        s.header_dirty = 1;
        s.full = 0;
    }
    if (s.header_dirty) {
        draw_header();
    }
    for (int i = 0; i < N * N; i++) {
        if (i == s.pop_cell && s.pop_frame > 0) {
            continue;
        }
        if (s.shown[i] != s.st.cell[i]) {
            draw_tile(i, 100);
            s.shown[i] = s.st.cell[i];
        }
    }
    if (s.pop_frame > 0) {
        draw_tile(s.pop_cell, s.pop_frame >= POP_FRAMES ? 100 : 40 + 60 * s.pop_frame / POP_FRAMES);
        if (s.pop_frame++ >= POP_FRAMES) {
            s.pop_frame = 0;
            s.shown[s.pop_cell] = s.st.cell[s.pop_cell];
        }
    }
    if (s.st.over == 1) {
        g_over("Game over", "Score ", s.st.score, "Best ", s.best, s.new_best);
        s.st.over = 2; /* drawn */
    }
    s3w_gfx_present();
}

void s3w_on_event(const s3w_event_t *e)
{
    if (s.st.over) {
        if (e->type == S3W_EV_TAP && g_may_restart()) {
            new_game();
        }
        return;
    }
    if (e->type != S3W_EV_SWIPE) {
        return;
    }
    if (s.pop_frame > 0) { /* finish the growing tile first */
        s.shown[s.pop_cell] = -1;
        s.pop_frame = 0;
    }
    int gained = 0, merges = 0;
    if (!slide(e->value, &gained, &merges)) {
        return;
    }
    s.st.score += gained;
    s.header_dirty = 1;
    if (merges) {
        s3w_audio_tone(523 + 40 * merges, 40, 40);
    }
    for (int i = 0; i < N * N; i++) {
        if (s.st.cell[i] == 2048 && !s.st.won) {
            s.st.won = 1;
            s3w_audio_tone(1047, 300, 60);
        }
    }
    spawn();
    if (!can_move()) {
        game_over();
    } else {
        if (s.st.won == 1 && gained == 0) {
            s.st.won = 2; /* the "2048!" line goes after the next plain move */
        }
        save();
    }
}
