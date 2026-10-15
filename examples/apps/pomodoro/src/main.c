/*
 * Pomodoro (preinstalled, widgets mode): 25 min focus, 5 min break, a 15 min break after every
 * fourth round. A ring and the time left; Start / Pause and Skip / Reset. When a phase ends: three
 * tones and a notification, and the next phase waits for Start. The screen stays on while the
 * timer runs. The time left is computed from s3w_millis(), so a late tick never drifts the clock;
 * the 1 s tick only redraws (and runs only while the timer does). The phase, round and time left
 * survive the app closing (kv "state"); a running timer comes back paused.
 */
#include "../../common/app_util.h"

#define FOCUS_S       (25 * 60)
#define SHORT_BREAK_S (5 * 60)
#define LONG_BREAK_S  (15 * 60)
#define ROUNDS        4

enum { PH_FOCUS = 0, PH_SHORT, PH_LONG };

static const char *const k_phase_name[] = {"Focus", "Short break", "Long break"};
static const int k_phase_color[] = {U_RED, U_GREEN, U_TEAL};

static struct {
    struct {
        int32_t phase;
        int32_t round;     /* 1..ROUNDS */
        int32_t left_ms;   /* while paused */
        int32_t done;      /* focus rounds finished (all time) */
    } st;
    int running;
    uint32_t end_ms;       /* s3w_millis() when the phase ends, while running */
    int tick;              /* the 1 s redraw timer */
    int beep, beeps_left;  /* the end-of-phase tones */
    int ring, time_label, phase_label, round_label, start_btn, skip_btn;
} s;

static int phase_len_s(int ph)
{
    return ph == PH_FOCUS ? FOCUS_S : ph == PH_SHORT ? SHORT_BREAK_S : LONG_BREAK_S;
}

static int left_ms(void)
{
    if (!s.running) {
        return s.st.left_ms;
    }
    const int32_t d = (int32_t)(s.end_ms - s3w_millis());
    return d > 0 ? d : 0;
}

static void save(void)
{
    const int32_t keep = s.st.left_ms;
    s.st.left_ms = left_ms();
    s3w_kv_set(STR("state"), &s.st, sizeof s.st);
    s.st.left_ms = keep;
}

static void show(void)
{
    const int ms = left_ms();
    const int sec = (ms + 999) / 1000;
    char t[48];
    int n = u_cat_int(t, 0, sec / 60);
    t[n++] = ':';
    n = u_cat_2d(t, n, sec % 60);
    s3w_ui_set_text(s.time_label, t, n);
    const int total = phase_len_s(s.st.phase);
    s3w_ui_set_value(s.ring, (total - sec) * 1000 / total);
    const char *name = k_phase_name[s.st.phase];
    s3w_ui_set_text(s.phase_label, name, u_strlen(name));
    s3w_ui_set_style(s.phase_label, S3W_STYLE_TEXT_COLOR, k_phase_color[s.st.phase]);
    n = u_cat(t, 0, "Round ");
    n = u_cat_int(t, n, s.st.round);
    n = u_cat(t, n, " of ");
    n = u_cat_int(t, n, ROUNDS);
    n = u_cat(t, n, " \xC2\xB7 ");
    n = u_cat_int(t, n, s.st.done);
    n = u_cat(t, n, " done");
    s3w_ui_set_text(s.round_label, t, n);
    if (s.running) {
        s3w_ui_set_text(s.start_btn, STR("Pause"));
    } else {
        u_set_text(s.start_btn, s.st.left_ms < total * 1000 ? "Resume" : "Start");
    }
    u_set_text(s.skip_btn, s.running ? "Skip" : "Reset");
}

static void set_running(int on)
{
    if (on == s.running) {
        return;
    }
    if (on) {
        s.end_ms = s3w_millis() + (uint32_t)s.st.left_ms;
        s.tick = s3w_timer_start(1000, true); /* 1 Hz: the seconds on screen, only while running */
    } else {
        s.st.left_ms = left_ms();
        if (s.tick > 0) {
            s3w_timer_stop(s.tick);
        }
        s.tick = 0;
    }
    s.running = on;
    s3w_keep_screen_on(on);
}

static void enter_phase(int ph)
{
    s.st.phase = ph;
    s.st.left_ms = phase_len_s(ph) * 1000;
}

/* The phase ended (or was skipped): on to the next one, waiting for Start. */
static void next_phase(int finished)
{
    set_running(0);
    if (s.st.phase == PH_FOCUS) {
        if (finished) {
            s.st.done++;
        }
        enter_phase(s.st.round >= ROUNDS ? PH_LONG : PH_SHORT);
    } else {
        s.st.round = s.st.phase == PH_LONG ? 1 : s.st.round + 1;
        enter_phase(PH_FOCUS);
    }
    save();
}

static void alarm(void)
{
    const int brk = s.st.phase != PH_FOCUS; /* the phase that starts now */
    const char *body = brk ? "Focus done: time for a break" : "Break over: back to focus";
    s3w_notify(STR("Pomodoro"), body, u_strlen(body));
    s.beeps_left = 3;
    s3w_audio_tone(880, 200, 80);
    s.beep = s3w_timer_start(400, true); /* the next two tones */
}

void s3w_on_start(void)
{
    if (s3w_kv_get(STR("state"), &s.st, sizeof s.st) != (int)sizeof s.st || s.st.phase < PH_FOCUS ||
        s.st.phase > PH_LONG || s.st.round < 1 || s.st.round > ROUNDS || s.st.left_ms < 0 ||
        s.st.left_ms > phase_len_s(s.st.phase) * 1000) {
        s.st.round = 1;
        s.st.done = 0;
        enter_phase(PH_FOCUS);
    }
    const int scr = s3w_ui_screen();
    s.ring = u_place(s3w_ui_arc(scr, 0, 1000, 0), S3W_ALIGN_TOP_MID, 0, 40);
    s3w_ui_set_size(s.ring, 280, 280);
    s.phase_label = u_label(scr, "", 0, S3W_FONT_BODY, U_RED, S3W_ALIGN_TOP_MID, 0, 78);
    s.time_label = u_label(scr, "", 0, S3W_FONT_DISPLAY, U_TEXT, S3W_ALIGN_TOP_MID, 0, 126);
    s.round_label = u_label(scr, "", 0, S3W_FONT_CAPTION, U_DIM, S3W_ALIGN_TOP_MID, 0, 250);
    s.start_btn = u_place(s3w_ui_button(scr, STR("Start")), S3W_ALIGN_TOP_MID, -84, 352);
    s3w_ui_set_size(s.start_btn, 156, 64);
    s.skip_btn = u_place(s3w_ui_button(scr, STR("Reset")), S3W_ALIGN_TOP_MID, 84, 352);
    s3w_ui_set_size(s.skip_btn, 156, 64);
    s3w_ui_set_style(s.skip_btn, S3W_STYLE_BG_COLOR, U_SURFACE2);
    show();
}

void s3w_on_stop(void)
{
    save();
}

void s3w_on_event(const s3w_event_t *e)
{
    if (e->type == S3W_EV_CLICK && e->handle == s.start_btn) {
        set_running(!s.running);
        save();
    } else if (e->type == S3W_EV_CLICK && e->handle == s.skip_btn) {
        if (s.running) {
            next_phase(0);
        } else {
            enter_phase(s.st.phase); /* back to the full time */
            save();
        }
    } else if (e->type == S3W_EV_TIMER && e->handle == s.tick) {
        if (left_ms() == 0) {
            next_phase(1);
            alarm();
        }
    } else if (e->type == S3W_EV_TIMER && e->handle == s.beep) {
        if (--s.beeps_left > 0) {
            s3w_audio_tone(s.beeps_left == 1 ? 1175 : 988, 200, 80);
        }
        if (s.beeps_left <= 1) {
            s3w_timer_stop(s.beep);
            s.beep = 0;
        }
        return;
    } else {
        return;
    }
    show();
}
