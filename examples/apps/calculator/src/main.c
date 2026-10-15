/*
 * Calculator (preinstalled, widgets mode): a four-function calculator that works left to right
 * like a pocket one (2 + 3 × 4 = 20), with ±, %, backspace and a history of the last ten results
 * (kv "hist"). The last result comes back when the app starts again (kv "last").
 */
#include "../../common/app_util.h"

#define ENTRY_MAX  10 /* digits typed */
#define HIST_MAX   10
#define HIST_LINE  40

enum { OP_NONE = 0, OP_ADD, OP_SUB, OP_MUL, OP_DIV };

static const char *const k_op_text[] = {"", "+", "-", "\xC3\x97", "\xC3\xB7"}; /* × ÷ */

/* The keys, row by row. */
enum {
    K_CLEAR, K_SIGN, K_PCT, K_DIV,
    K_7, K_8, K_9, K_MUL,
    K_4, K_5, K_6, K_SUB,
    K_1, K_2, K_3, K_ADD,
    K_0, K_DOT, K_BACK, K_EQ,
    K_COUNT
};
static const char *const k_key_text[K_COUNT] = {
    "C", "\xC2\xB1", "%", "\xC3\xB7",
    "7", "8", "9", "\xC3\x97",
    "4", "5", "6", "-",
    "1", "2", "3", "+",
    "0", ".", "\xEF\x95\x9A", "=", /* backspace symbol */
};

static struct {
    double acc;           /* the left operand */
    int op;               /* pending operator */
    char entry[24];       /* what the display shows: typed digits or a result */
    int entry_len;
    int fresh;            /* the next digit starts a new entry */
    int error;
    char expr[64];        /* the line above: "12 + 7 =" */
    int expr_len;
    char hist[HIST_MAX][HIST_LINE];
    int hist_n;
    /* Widgets */
    int scr, keys[K_COUNT], expr_label, display, hist_button;
    int list, list_back, list_clear;
} s;

/* --- Numbers ------------------------------------------------------------------------------ */

static double parse(const char *t, int n)
{
    double v = 0, scale = 0;
    int neg = 0;
    for (int i = 0; i < n; i++) {
        if (t[i] == '-') {
            neg = 1;
        } else if (t[i] == '.') {
            scale = 1;
        } else if (t[i] >= '0' && t[i] <= '9') {
            v = v * 10 + (t[i] - '0');
            if (scale) {
                scale *= 10;
            }
        }
    }
    if (scale) {
        v /= scale;
    }
    return neg ? -v : v;
}

static void set_entry_value(double v)
{
    s.entry_len = u_cat_num(s.entry, 0, v, 10);
}

static double entry_value(void)
{
    return parse(s.entry, s.entry_len);
}

static double apply(double a, int op, double b, int *err)
{
    switch (op) {
    case OP_ADD: return a + b;
    case OP_SUB: return a - b;
    case OP_MUL: return a * b;
    case OP_DIV:
        if (b == 0) {
            *err = 1;
            return 0;
        }
        return a / b;
    default: return b;
    }
}

/* --- Display ------------------------------------------------------------------------------ */

static int display_font_ok(void)
{
    if (s.entry_len > 7) {
        return 0;
    }
    for (int i = 0; i < s.entry_len; i++) {
        const char c = s.entry[i];
        if (!((c >= '0' && c <= '9') || c == '.' || c == '-')) {
            return 0; /* "e" and "Error": the display font has digits only */
        }
    }
    return 1;
}

static void show(void)
{
    if (!s.display) {
        return;
    }
    if (s.error) {
        s3w_ui_set_style(s.display, S3W_STYLE_FONT, S3W_FONT_TITLE);
        s3w_ui_set_text(s.display, STR("Error"));
    } else {
        s3w_ui_set_style(s.display, S3W_STYLE_FONT, display_font_ok() ? S3W_FONT_DISPLAY : S3W_FONT_TITLE);
        s3w_ui_set_text(s.display, s.entry, s.entry_len);
    }
    s3w_ui_set_text(s.expr_label, s.expr, s.expr_len);
}

/* --- History ------------------------------------------------------------------------------ */

static void hist_save(void)
{
    char blob[HIST_MAX * HIST_LINE];
    int n = 0;
    for (int i = 0; i < s.hist_n; i++) {
        n = u_cat(blob, n, s.hist[i]);
        blob[n++] = '\n';
    }
    s3w_kv_set(STR("hist"), blob, n);
}

static void hist_load(void)
{
    char blob[HIST_MAX * HIST_LINE];
    const int n = s3w_kv_get(STR("hist"), blob, sizeof blob);
    s.hist_n = 0;
    int len = 0;
    for (int i = 0; i < n && s.hist_n < HIST_MAX; i++) {
        if (blob[i] == '\n') {
            s.hist[s.hist_n++][len] = '\0';
            len = 0;
        } else if (len < HIST_LINE - 1) {
            s.hist[s.hist_n][len++] = blob[i];
        }
    }
}

/* Newest first. */
static void hist_push(const char *line, int len)
{
    if (s.hist_n == HIST_MAX) {
        s.hist_n--;
    }
    for (int i = s.hist_n; i > 0; i--) {
        for (int k = 0; k < HIST_LINE; k++) {
            s.hist[i][k] = s.hist[i - 1][k];
        }
    }
    if (len > HIST_LINE - 1) {
        len = HIST_LINE - 1;
    }
    for (int k = 0; k < len; k++) {
        s.hist[0][k] = line[k];
    }
    s.hist[0][len] = '\0';
    s.hist_n++;
    hist_save();
}

/* --- Keys --------------------------------------------------------------------------------- */

static void clear_all(void)
{
    s.acc = 0;
    s.op = OP_NONE;
    s.entry[0] = '0';
    s.entry_len = 1;
    s.fresh = 1;
    s.error = 0;
    s.expr_len = 0;
}

static void save_last(void)
{
    const double v = s.error ? 0 : entry_value();
    s3w_kv_set(STR("last"), &v, sizeof v);
}

static void digit(char c)
{
    if (s.error) {
        clear_all();
    }
    if (s.fresh) {
        s.entry_len = 0;
        s.fresh = 0;
        if (s.op == OP_NONE) {
            s.expr_len = 0;
        }
    }
    int digits = 0;
    int has_dot = 0;
    for (int i = 0; i < s.entry_len; i++) {
        digits += s.entry[i] >= '0' && s.entry[i] <= '9';
        has_dot |= s.entry[i] == '.';
    }
    if (c == '.') {
        if (has_dot) {
            return;
        }
        if (s.entry_len == 0 || (s.entry_len == 1 && s.entry[0] == '-')) {
            s.entry[s.entry_len++] = '0';
        }
    } else if (digits >= ENTRY_MAX) {
        return;
    } else if (s.entry_len == 1 && s.entry[0] == '0') {
        s.entry_len = 0; /* no leading zero */
    } else if (s.entry_len == 2 && s.entry[0] == '-' && s.entry[1] == '0') {
        s.entry_len = 1;
    }
    s.entry[s.entry_len++] = c;
}

static void expr_operand(double a, int op)
{
    s.expr_len = u_cat_num(s.expr, 0, a, 10);
    s.expr[s.expr_len++] = ' ';
    s.expr_len = u_cat(s.expr, s.expr_len, k_op_text[op]);
}

static void operator(int op)
{
    if (s.error) {
        return;
    }
    if (s.op != OP_NONE && !s.fresh) {
        int err = 0;
        s.acc = apply(s.acc, s.op, entry_value(), &err);
        if (err) {
            s.error = 1;
            return;
        }
        set_entry_value(s.acc);
    } else if (s.op == OP_NONE) {
        s.acc = entry_value();
    }
    s.op = op;
    s.fresh = 1;
    expr_operand(s.acc, op);
}

static void equals(void)
{
    if (s.error || s.op == OP_NONE) {
        return;
    }
    const double b = entry_value();
    int err = 0;
    const double r = apply(s.acc, s.op, b, &err);
    expr_operand(s.acc, s.op);
    s.expr[s.expr_len++] = ' ';
    s.expr_len = u_cat_num(s.expr, s.expr_len, b, 10);
    s.expr_len = u_cat(s.expr, s.expr_len, " =");
    s.op = OP_NONE;
    s.fresh = 1;
    if (err) {
        s.error = 1;
        return;
    }
    set_entry_value(r);
    if (s.entry[0] == 'E') {
        s.error = 1; /* overflow */
        return;
    }
    char line[HIST_LINE + 24];
    int n = 0;
    for (int i = 0; i < s.expr_len - 1 && n < HIST_LINE; i++) {
        line[n++] = s.expr[i];
    }
    n = u_cat(line, n, "= ");
    for (int i = 0; i < s.entry_len; i++) {
        line[n++] = s.entry[i];
    }
    hist_push(line, n);
    save_last();
}

static void key(int k)
{
    switch (k) {
    case K_CLEAR: clear_all(); break;
    case K_SIGN:
        if (!s.error) {
            if (s.entry[0] == '-') {
                for (int i = 1; i < s.entry_len; i++) {
                    s.entry[i - 1] = s.entry[i];
                }
                s.entry_len--;
            } else if (!(s.entry_len == 1 && s.entry[0] == '0')) {
                for (int i = s.entry_len; i > 0; i--) {
                    s.entry[i] = s.entry[i - 1];
                }
                s.entry[0] = '-';
                s.entry_len++;
            }
            if (s.fresh && s.op == OP_NONE) {
                s.fresh = 0; /* edit the result */
            }
        }
        break;
    case K_PCT:
        if (!s.error) {
            /* 200 + 10 % = 220: a percentage of the left operand for + and -. */
            const double v = entry_value() / 100;
            set_entry_value(s.op == OP_ADD || s.op == OP_SUB ? s.acc * v : v);
            s.fresh = s.op == OP_NONE;
        }
        break;
    case K_BACK:
        if (!s.error && !s.fresh) {
            s.entry_len--;
            if (s.entry_len == 0 || (s.entry_len == 1 && s.entry[0] == '-')) {
                s.entry[0] = '0';
                s.entry_len = 1;
            }
        }
        break;
    case K_ADD: operator(OP_ADD); break;
    case K_SUB: operator(OP_SUB); break;
    case K_MUL: operator(OP_MUL); break;
    case K_DIV: operator(OP_DIV); break;
    case K_EQ: equals(); break;
    case K_DOT: digit('.'); break;
    case K_0: digit('0'); break;
    case K_1: digit('1'); break;
    case K_2: digit('2'); break;
    case K_3: digit('3'); break;
    case K_4: digit('4'); break;
    case K_5: digit('5'); break;
    case K_6: digit('6'); break;
    case K_7: digit('7'); break;
    case K_8: digit('8'); break;
    case K_9: digit('9'); break;
    default: break;
    }
    show();
}

/* --- Pages -------------------------------------------------------------------------------- */

#define KEY_W   80
#define KEY_H   58
#define KEY_GAP 6
#define KEYS_Y  162

static void build_keypad(void)
{
    s.list = 0;
    s.hist_button = u_place(s3w_ui_button(s.scr, STR("\xEF\x80\x8B")), S3W_ALIGN_TOP_LEFT, 56, 64); /* list */
    s3w_ui_set_size(s.hist_button, 56, 44);
    s3w_ui_set_style(s.hist_button, S3W_STYLE_BG_COLOR, U_SURFACE2);
    s.expr_label = u_label(s.scr, "", 0, S3W_FONT_CAPTION, U_DIM, S3W_ALIGN_TOP_RIGHT, -40, 14);
    s.display = s3w_ui_label(s.scr, "", 0);
    s3w_ui_set_style(s.display, S3W_STYLE_TEXT_ALIGN, S3W_TEXT_ALIGN_RIGHT);
    u_place(s.display, S3W_ALIGN_TOP_RIGHT, -40, 46);
    const int x0 = (S3W_SCREEN_W - 4 * KEY_W - 3 * KEY_GAP) / 2;
    for (int k = 0; k < K_COUNT; k++) {
        const int row = k / 4, col = k % 4;
        const int h = s3w_ui_button(s.scr, k_key_text[k], u_strlen(k_key_text[k]));
        u_place(h, S3W_ALIGN_TOP_LEFT, x0 + col * (KEY_W + KEY_GAP), KEYS_Y + row * (KEY_H + KEY_GAP));
        s3w_ui_set_size(h, KEY_W, KEY_H);
        s3w_ui_set_style(h, S3W_STYLE_FONT, S3W_FONT_TITLE);
        int bg = U_SURFACE2;
        if (col == 3) {
            bg = U_ORANGE;
        } else if (row == 0) {
            bg = 0x48484A;
        }
        s3w_ui_set_style(h, S3W_STYLE_BG_COLOR, bg);
        s.keys[k] = h;
    }
    show();
}

static void delete_keypad(void)
{
    s3w_ui_delete(s.hist_button);
    s3w_ui_delete(s.expr_label);
    s3w_ui_delete(s.display);
    for (int k = 0; k < K_COUNT; k++) {
        s3w_ui_delete(s.keys[k]);
        s.keys[k] = 0;
    }
    s.hist_button = s.expr_label = s.display = 0;
}

static void build_history(void)
{
    s.list = s3w_ui_list(s.scr);
    s.list_back = s3w_ui_list_add(s.list, S3W_ICON_LEFT, STR("Calculator"));
    for (int i = 0; i < s.hist_n; i++) {
        s3w_ui_list_add(s.list, S3W_ICON_NONE, s.hist[i], u_strlen(s.hist[i]));
    }
    if (s.hist_n == 0) {
        s3w_ui_list_add(s.list, S3W_ICON_NONE, STR("No calculations yet"));
        s.list_clear = 0;
    } else {
        s.list_clear = s3w_ui_list_add(s.list, S3W_ICON_TRASH, STR("Clear history"));
    }
}

void s3w_on_start(void)
{
    hist_load();
    clear_all();
    double last;
    if (s3w_kv_get(STR("last"), &last, sizeof last) == (int)sizeof last && last == last) {
        set_entry_value(last);
    }
    s.scr = s3w_ui_screen();
    build_keypad();
}

void s3w_on_event(const s3w_event_t *e)
{
    if (e->type != S3W_EV_CLICK) {
        return;
    }
    if (s.list) {
        if (e->handle == s.list_back) {
            s3w_ui_delete(s.list);
            build_keypad();
        } else if (s.list_clear && e->handle == s.list_clear) {
            s.hist_n = 0;
            hist_save();
            s3w_ui_delete(s.list);
            build_history();
        }
        return;
    }
    if (e->handle == s.hist_button) {
        delete_keypad();
        build_history();
        return;
    }
    for (int k = 0; k < K_COUNT; k++) {
        if (e->handle == s.keys[k]) {
            key(k);
            return;
        }
    }
}
