/*
 * Canvas helpers shared by the preinstalled games (P8-08): centred text, rounded rectangles, the
 * title / game-over screens and the high-score line. Include after app_util.h.
 *
 * Drawing on the watch costs per pixel copied to the display: games redraw only what changed
 * (a cell, a sprite's old and new box), never the whole screen per frame.
 */
#ifndef S3W_GAME_UTIL_H
#define S3W_GAME_UTIL_H

#include "app_util.h"

#define G_W  S3W_SCREEN_W
#define G_H  S3W_SCREEN_H
#define G_CX (S3W_SCREEN_W / 2)

#define G_BLACK  S3W_RGB565(0, 0, 0)
#define G_WHITE  S3W_RGB565(0xFF, 0xFF, 0xFF)
#define G_DIM    S3W_RGB565(0x9A, 0x9A, 0xA0)
#define G_DARK   S3W_RGB565(0x1C, 0x1C, 0x1E)
#define G_DARK2  S3W_RGB565(0x2C, 0x2C, 0x2E)
#define G_ACCENT S3W_RGB565(0x3D, 0x8B, 0xFF)
#define G_GREEN  S3W_RGB565(0x30, 0xD1, 0x58)
#define G_RED    S3W_RGB565(0xFF, 0x45, 0x3A)
#define G_ORANGE S3W_RGB565(0xFF, 0x9F, 0x0A)
#define G_YELLOW S3W_RGB565(0xFF, 0xD6, 0x0A)
#define G_PURPLE S3W_RGB565(0xBF, 0x5A, 0xF2)
#define G_TEAL   S3W_RGB565(0x40, 0xC8, 0xE0)

/* Text centred on x = cx, top at y. */
static inline void g_text_at(int cx, int y, const char *t, int n, int font, uint16_t color)
{
    s3w_gfx_text(cx - s3w_gfx_text_width(t, n, font) / 2, y, t, n, font, color);
}

static inline void g_text(int y, const char *t, int font, uint16_t color)
{
    g_text_at(G_CX, y, t, u_strlen(t), font, color);
}

/* "<label><n>" centred. */
static inline void g_text_num(int y, const char *label, int n, int font, uint16_t color)
{
    char t[32];
    int len = u_cat(t, 0, label);
    len = u_cat_int(t, len, n);
    g_text_at(G_CX, y, t, len, font, color);
}

/* Stays inside (x, y, w, h): a corner circle of radius r is 2r + 1 px across. */
static inline void g_rrect(int x, int y, int w, int h, int r, uint16_t c)
{
    if (r * 2 + 1 > w) {
        r = (w - 1) / 2;
    }
    if (r * 2 + 1 > h) {
        r = (h - 1) / 2;
    }
    if (r <= 0) {
        s3w_gfx_rect(x, y, w, h, c, true);
        return;
    }
    s3w_gfx_rect(x + r, y, w - 2 * r, h, c, true);
    s3w_gfx_rect(x, y + r, r, h - 2 * r, c, true);
    s3w_gfx_rect(x + w - r, y + r, r, h - 2 * r, c, true);
    s3w_gfx_circle(x + r, y + r, r, c, true);
    s3w_gfx_circle(x + w - 1 - r, y + r, r, c, true);
    s3w_gfx_circle(x + r, y + h - 1 - r, r, c, true);
    s3w_gfx_circle(x + w - 1 - r, y + h - 1 - r, r, c, true);
}

/* Clears a band across the screen (inside the rounded corners' safe area). */
static inline void g_band(int y, int h, uint16_t bg)
{
    s3w_gfx_rect(0, y, G_W, h, bg, true);
}

/* The board's best, or 0 before the first score. */
static inline int g_best(int board)
{
    int best = 0;
    return s3w_highscore_get(board, &best) == S3W_OK ? best : 0;
}

/* Title screen: name, the best score line (if any), a hint. The caller draws its art between
 * y 120 and 360. */
static inline void g_title(const char *name, const char *best_label, int best, int has_best, const char *hint,
                           uint16_t bg)
{
    s3w_gfx_clear(bg);
    g_text(52, name, S3W_FONT_TITLE, G_WHITE);
    if (has_best) {
        g_text_num(92, best_label, best, S3W_FONT_CAPTION, G_DIM);
    }
    g_text(400, hint, S3W_FONT_BODY, G_WHITE);
}

/* When the last game ended (g_over / g_ended), so a tap meant for the game does not start the
 * next one at once. */
static uint32_t g_ended_ms;
static int g_has_ended;

static inline void g_ended(void)
{
    g_ended_ms = s3w_millis();
    g_has_ended = 1;
}

/* A tap may start a new game: at once on the title screen, 700 ms after a game ended. */
static inline int g_may_restart(void)
{
    return !g_has_ended || s3w_millis() - g_ended_ms >= 700;
}

/* Game-over panel over the board: title, score, best (with "New best!"), hint. */
static inline void g_over(const char *title, const char *score_label, int score, const char *best_label, int best,
                          int new_best)
{
    g_ended();
    g_rrect(45, 150, G_W - 90, 210, 28, G_DARK);
    g_text(170, title, S3W_FONT_TITLE, G_WHITE);
    g_text_num(218, score_label, score, S3W_FONT_BODY, G_WHITE);
    if (new_best) {
        g_text(256, "New best!", S3W_FONT_BODY, G_YELLOW);
    } else {
        g_text_num(256, best_label, best, S3W_FONT_BODY, G_DIM);
    }
    g_text(310, "Tap to play again", S3W_FONT_CAPTION, G_DIM);
}

#endif /* S3W_GAME_UTIL_H */
