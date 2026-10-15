/*
 * Small helpers shared by the preinstalled apps (apps/<name>/src/main.c includes this as
 * "../../common/app_util.h"). Freestanding C: no libc, so text formatting, a PRNG and a few maths
 * helpers live here. Everything is static inline: an app pays only for what it uses.
 */
#ifndef S3W_APP_UTIL_H
#define S3W_APP_UTIL_H

#include "s3w.h"

/* A string literal as (pointer, length). */
#define STR(s) s, (int)(sizeof(s) - 1)

static inline int u_strlen(const char *s)
{
    int n = 0;
    while (s[n]) {
        n++;
    }
    return n;
}

/* Appends s at buf + len; returns the new length (no terminator). */
static inline int u_cat(char *buf, int len, const char *s)
{
    while (*s) {
        buf[len++] = *s++;
    }
    return len;
}

/* Appends n in decimal; returns the new length. */
static inline int u_cat_int(char *buf, int len, long long n)
{
    char d[20];
    int k = 0;
    unsigned long long u = n < 0 ? (unsigned long long)-n : (unsigned long long)n;
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

/* Appends n with at least two digits ("07"). */
static inline int u_cat_2d(char *buf, int len, int n)
{
    if (n < 10 && n >= 0) {
        buf[len++] = '0';
    }
    return u_cat_int(buf, len, n);
}

/* Appends "m:ss" (or "h:mm:ss" from an hour on) for seconds. */
static inline int u_cat_mmss(char *buf, int len, int seconds)
{
    if (seconds >= 3600) {
        len = u_cat_int(buf, len, seconds / 3600);
        buf[len++] = ':';
        len = u_cat_2d(buf, len, seconds / 60 % 60);
    } else {
        len = u_cat_int(buf, len, seconds / 60);
    }
    buf[len++] = ':';
    return u_cat_2d(buf, len, seconds % 60);
}

/* Appends v rounded to decimals (0..6) places, trailing zeros (and a lone point) removed when
 * trim. */
static inline int u_cat_fixed(char *buf, int len, double v, int decimals, int trim)
{
    long long scale = 1;
    for (int i = 0; i < decimals; i++) {
        scale *= 10;
    }
    const int neg = v < 0;
    const double a = neg ? -v : v;
    unsigned long long r = (unsigned long long)(a * (double)scale + 0.5);
    unsigned long long whole = r / (unsigned long long)scale;
    unsigned long long frac = r % (unsigned long long)scale;
    if (neg && r != 0) {
        buf[len++] = '-';
    }
    len = u_cat_int(buf, len, (long long)whole);
    if (decimals > 0) {
        char f[8];
        for (int i = decimals - 1; i >= 0; i--) {
            f[i] = (char)('0' + frac % 10);
            frac /= 10;
        }
        int n = decimals;
        while (trim && n > 0 && f[n - 1] == '0') {
            n--;
        }
        if (n > 0) {
            buf[len++] = '.';
            for (int i = 0; i < n; i++) {
                buf[len++] = f[i];
            }
        }
    }
    return len;
}

/* Appends v with up to sig significant digits (1..15) in plain notation when that fits in about
 * sig + 2 characters, else as "1.2345e12". */
static inline int u_cat_num(char *buf, int len, double v, int sig)
{
    if (v != v) {
        return u_cat(buf, len, "Error");
    }
    if (v < 0) {
        buf[len++] = '-';
        v = -v;
    }
    if (v > 1.7e308) {
        return u_cat(buf, len, "Error");
    }
    if (v == 0) {
        buf[len++] = '0';
        return len;
    }
    /* Decimal exponent of the first significant digit. */
    int e = 0;
    double m = v;
    while (m >= 10) {
        m /= 10;
        e++;
    }
    while (m < 1) {
        m *= 10;
        e--;
    }
    /* Round to sig digits; carrying can make m 10. */
    double p = 1;
    for (int i = 1; i < sig; i++) {
        p *= 10;
    }
    unsigned long long digits = (unsigned long long)(m * p + 0.5);
    if ((double)digits >= p * 10) {
        digits /= 10;
        e++;
    }
    char d[16];
    for (int i = sig - 1; i >= 0; i--) {
        d[i] = (char)('0' + digits % 10);
        digits /= 10;
    }
    int n = sig;
    while (n > 1 && d[n - 1] == '0') {
        n--;
    }
    if (e >= sig || e < -4) { /* scientific */
        buf[len++] = d[0];
        if (n > 1) {
            buf[len++] = '.';
            for (int i = 1; i < n; i++) {
                buf[len++] = d[i];
            }
        }
        buf[len++] = 'e';
        return u_cat_int(buf, len, e);
    }
    if (e < 0) {
        buf[len++] = '0';
        buf[len++] = '.';
        for (int i = -1; i > e; i--) {
            buf[len++] = '0';
        }
        for (int i = 0; i < n; i++) {
            buf[len++] = d[i];
        }
        return len;
    }
    for (int i = 0; i <= e; i++) {
        buf[len++] = i < n ? d[i] : '0';
    }
    if (n > e + 1) {
        buf[len++] = '.';
        for (int i = e + 1; i < n; i++) {
            buf[len++] = d[i];
        }
    }
    return len;
}

/* Days since 1970-01-01 for a civil date (any year >= 1970). */
static inline int32_t u_days(int y, int m, int d)
{
    y -= m <= 2;
    const int era = y / 400;
    const int yoe = y - era * 400;
    const int doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    const int doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + doe - 719468;
}

/* Today as u_days(), or -1 while the watch does not know the date. */
static inline int32_t u_today(void)
{
    s3w_tm_t tm;
    return s3w_time_local(&tm) == S3W_OK ? u_days(tm.year, tm.month, tm.day) : -1;
}

/* xorshift32: a small PRNG for dice and the like. Seed with something that changes. */
static inline uint32_t u_rand(uint32_t *state)
{
    uint32_t x = *state ? *state : 0x9E3779B9u;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

static inline int u_clamp(int v, int lo, int hi)
{
    return v < lo ? lo : v > hi ? hi : v;
}

static inline float u_absf(float v)
{
    return v < 0 ? -v : v;
}

/* sin(x) for any x (radians), |error| < 0.001: enough for animation. */
static inline float u_sinf(float x)
{
    const float pi = 3.14159265f, two_pi = 6.2831853f;
    x -= two_pi * (float)(int)(x / two_pi);
    if (x > pi) {
        x -= two_pi;
    } else if (x < -pi) {
        x += two_pi;
    }
    /* Bhaskara-style parabola, refined. */
    float y = 1.27323954f * x - 0.40528473f * x * u_absf(x);
    return 0.225f * (y * u_absf(y) - y) + y;
}

static inline float u_cosf(float x)
{
    return u_sinf(x + 1.57079633f);
}

/* A label's or button's text from a C string. */
static inline void u_set_text(int h, const char *t)
{
    s3w_ui_set_text(h, t, u_strlen(t));
}

/* Places h in its parent: align (S3W_ALIGN_*) plus an offset. */
static inline int u_place(int h, int align, int x, int y)
{
    s3w_ui_set_style(h, S3W_STYLE_ALIGN, align);
    s3w_ui_set_pos(h, x, y);
    return h;
}

/* A label with a font and colour, placed. */
static inline int u_label(int parent, const char *t, int len, int font, int color, int align, int x, int y)
{
    const int h = s3w_ui_label(parent, t, len);
    s3w_ui_set_style(h, S3W_STYLE_FONT, font);
    s3w_ui_set_style(h, S3W_STYLE_TEXT_COLOR, color);
    return u_place(h, align, x, y);
}

/* Theme colours. */
#define U_TEXT     0xFFFFFF
#define U_DIM      0x9A9AA0
#define U_SURFACE  0x1C1C1E
#define U_SURFACE2 0x2C2C2E
#define U_ACCENT   0x3D8BFF
#define U_ORANGE   0xFF9F0A
#define U_GREEN    0x30D158
#define U_RED      0xFF453A
#define U_PURPLE   0xBF5AF2
#define U_TEAL     0x40C8E0

#endif /* S3W_APP_UTIL_H */
