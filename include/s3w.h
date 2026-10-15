/*
 * s3w.h — the S3Wear mini app API, api_level 1.
 *
 * Apps are WebAssembly modules. Every function below is an import from module "s3w"; the app
 * exports the lifecycle callbacks it wants (all optional). Handles are small integers, never
 * pointers into firmware memory. Strings are UTF-8 (pointer, length) in app memory; the runtime
 * checks that every pointer argument lies inside the app's memory and traps the app if not.
 *
 * Error handling: functions that return int give a value >= 0 on success, or a negative
 * S3W_ERR_*. Calling a function with a handle that is not live (never made, deleted, or of the
 * wrong kind) traps the app: that is a bug in the app, not a runtime condition.
 *
 * The same header is compiled into the firmware (for the types and constants); the import
 * declarations are only visible when compiling for wasm.
 *
 * Implemented: lifecycle, system, timers, widgets mode, canvas mode, input, sensors, audio, storage,
 * health, network, notifications, packages, game services, device files (api_level 2) and the
 * Game Boy core (api_level 3).
 *
 * Documentation tags (read by the API reference generator): every function carries `@since N` (the api_level that
 * added it) and, if it needs a permission, `@perm x`.
 *
 * Permissions: functions tagged @perm x need permission x in the app's manifest;
 * calling one without it traps the app. (The firmware's built-in samples get theirs from the
 * firmware.)
 *
 * UI mode: the manifest's "ui_mode" (a built-in sample: canvas mode when it exports s3w_on_frame,
 * else widgets mode). Calling a function of the other mode
 * traps, except s3w_ui_toast and s3w_ui_dialog (both modes) and s3w_ui_screen (S3W_ERR_UNSUPPORTED
 * in canvas mode).
 */
#ifndef S3W_H
#define S3W_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 2 adds the device file functions (s3w_fs_*, s3w_ui_image_file), 3 the Game Boy core (s3w_gb_*); a manifest
 * with api_level 3 does not install on firmware that only has level 2. */
#define S3W_API_LEVEL 3

/* --- Errors ------------------------------------------------------------------------------- */
#define S3W_OK               0
#define S3W_ERR_INVALID      (-1) /* an argument is out of range */
#define S3W_ERR_NO_RESOURCE  (-2) /* a limit is reached (512 UI handles, 8 timers, ...) */
#define S3W_ERR_NOT_FOUND    (-3) /* no such asset, ... */
#define S3W_ERR_UNSUPPORTED  (-4) /* not available on this watch or api_level */
#define S3W_ERR_NOT_READY    (-5) /* e.g. the wall clock is not set yet, no phone connected */
#define S3W_ERR_DENIED       (-6) /* refused: a host not in the manifest's allowlist, ... */
#define S3W_ERR_IO           (-7) /* storage failed */
#define S3W_ERR_NO_SPACE     (-8) /* the app's storage quota is full */
#define S3W_ERR_TIMEOUT      (-9) /* no answer in time (HTTP: 20 s) */
#define S3W_ERR_NETWORK      (-10) /* the phone could not reach the server */

/* --- Events (s3w_on_event) ---------------------------------------------------------------- */
enum {
    S3W_EV_TIMER = 1,  /* handle = timer id */
    S3W_EV_CLICK = 2,  /* handle = button or list row */
    S3W_EV_VALUE = 3,  /* handle = slider or switch, value = new value (switch: 0/1) */
    S3W_EV_DIALOG = 4, /* handle = dialog id from s3w_ui_dialog, value = 1 ok, 0 cancelled */
    /* Touch, canvas mode only (x, y: canvas px). Widgets mode has CLICK and VALUE instead. */
    S3W_EV_TOUCH_DOWN = 5,
    S3W_EV_TOUCH_MOVE = 6,  /* at most every 30 ms */
    S3W_EV_TOUCH_UP = 7,
    S3W_EV_TAP = 8,         /* a short press */
    S3W_EV_LONG_PRESS = 9,  /* held, without moving */
    S3W_EV_SWIPE = 10,      /* value = S3W_DIR_* */
    S3W_EV_IMU = 11,        /* x, y, value = acceleration x, y, z in mg (watch frame: +x to 3 o'clock,
                               +y to 12, +z out of the screen); handle = samples since the last
                               event (later samples replace earlier ones while the app is busy) */
    S3W_EV_HTTP = 12,       /* handle = request id, value = HTTP status or S3W_ERR_*, x = body
                               bytes written to resp, y = 1 if the body was cut at resp_cap */
    S3W_EV_BUTTON = 13,     /* a hardware button of an app whose manifest has "capture_back": true, while its
                               screen is up. handle = S3W_BTN_*, value = 1 pressed, 0 released. The system
                               then does nothing with that button (no back, no shortcut); PWR still goes home. */
};
#define S3W_BTN_BOOT 0

/* S3W_EV_SWIPE directions (where the finger went). The screen's edges and the buttons belong to
 * the system (back, home). */
enum { S3W_DIR_LEFT = 1, S3W_DIR_RIGHT, S3W_DIR_UP, S3W_DIR_DOWN };

typedef struct {
    int32_t type;   /* S3W_EV_* */
    int32_t handle;
    int32_t value;
    int32_t x, y;   /* touch and IMU events */
    int32_t reserved[3];
} s3w_event_t;      /* 32 bytes, layout fixed for api_level 1 */

/* Local time (s3w_time_local). */
typedef struct {
    int32_t year;   /* e.g. 2026 */
    int32_t month;  /* 1..12 */
    int32_t day;    /* 1..31 */
    int32_t hour;   /* 0..23 */
    int32_t minute; /* 0..59 */
    int32_t second; /* 0..59 */
    int32_t wday;   /* 0 = Sunday */
    int32_t yday;   /* 0..365 */
} s3w_tm_t;

/* s3w_health_today. */
typedef struct {
    int32_t steps;
    int32_t distance_m;
    int32_t active_min;
    int32_t kcal;
    int32_t sleep_min;  /* last night */
    int32_t resting_hr; /* 0: unknown (no heart rate sensor) */
    int32_t reserved[2];
} s3w_health_summary_t; /* 32 bytes, layout fixed for api_level 1 */

/* s3w_file_open modes. */
enum { S3W_FILE_READ = 0, S3W_FILE_WRITE = 1 /* create or truncate */, S3W_FILE_APPEND = 2 };

/* Game Boy core (api_level 3, functions below): buttons, sizes and the cartridge info. */
#define S3W_GB_A      0x01 /* s3w_gb_input mask: 1 = pressed */
#define S3W_GB_B      0x02
#define S3W_GB_SELECT 0x04
#define S3W_GB_START  0x08
#define S3W_GB_RIGHT  0x10
#define S3W_GB_LEFT   0x20
#define S3W_GB_UP     0x40
#define S3W_GB_DOWN   0x80
#define S3W_GB_W      160 /* the emulated screen */
#define S3W_GB_H      144
#define S3W_GB_SCALE_1X   2 /* s3w_gb_run_frame scale: twice the factor */
#define S3W_GB_SCALE_2X   4
#define S3W_GB_SCALE_2_5X 5
#define S3W_GB_NO_DRAW    1 /* s3w_gb_run_frame flags: emulate only (the core skips its pixel work too) */
#define S3W_GB_REDRAW     2 /* write every line, not only the changed ones */
typedef struct {
    char title[16];      /* cartridge header title, NUL padded, printable ASCII */
    uint8_t mapper;      /* 0 none, 1 MBC1, 2 MBC2, 3 MBC3, 5 MBC5; 0xFF: not supported */
    uint8_t cgb_flag;    /* header byte 0x143: 0 DMG, 0x80 DMG and CGB, 0xC0 CGB only */
    uint16_t rom_banks;  /* 16 KiB banks the header declares */
    uint8_t ram_kb;      /* cartridge RAM in KiB */
    uint8_t has_battery; /* the game keeps a save */
    uint8_t has_rtc;     /* MBC3 clock */
    uint8_t supported;   /* 1: this core can run it */
    uint32_t key;        /* CRC-32 of header bytes 0x100..0x14F: a stable id for per-game settings */
    uint8_t reserved[4];
} s3w_gb_info_t;         /* 32 bytes, layout fixed for api_level 3 */
/* Device files (api_level 2, functions below): limits and the list entry. */
#define S3W_FS_PATH_MAX 190
#define S3W_FS_NAME_MAX 95
#define S3W_FS_DIR      1 /* s3w_fs_entry_t.flags: a directory (size 0) */
typedef struct {
    char name[96];                   /* NUL terminated, S3W_FS_NAME_MAX + 1 bytes */
    uint32_t size;                  /* bytes; 0 for a directory */
    uint32_t flags;                 /* S3W_FS_* */
} s3w_fs_entry_t;                   /* 104 bytes */

/* s3w_http_request methods. */
enum { S3W_HTTP_GET = 0, S3W_HTTP_POST = 1 };

/* Limits. */
#define S3W_FILE_IMAGE_MAX_PIXELS 524288  /* s3w_ui_image_file: PNG and BMP, half a megapixel */
#define S3W_FILE_JPEG_MAX_PIXELS  8388608 /* JPEG, 8 megapixels */
#define S3W_FILE_IMAGE_MAX_SIDE   512
#define S3W_STORAGE_DEFAULT_KB 256   /* without the "storage" permission */
#define S3W_NAME_MAX           32    /* kv keys and file names */
#define S3W_KV_VALUE_MAX       4096
#define S3W_FILES_OPEN_MAX     4
#define S3W_HTTP_URL_MAX       511
#define S3W_HTTP_BODY_MAX      4096   /* request body */
#define S3W_HTTP_RESP_MAX      65536  /* response body */
#define S3W_HTTP_MAX           2      /* requests at once */
#define S3W_HIGHSCORE_BOARDS   8      /* boards 0..7 per app */
#define S3W_HIGHSCORE_LOWER    0x100  /* or into a board for s3w_highscore_submit: lower is better */

/* Log levels (s3w_log). */
enum { S3W_LOG_ERROR = 0, S3W_LOG_WARN = 1, S3W_LOG_INFO = 2, S3W_LOG_DEBUG = 3 };

/* --- Widgets mode constants --------------------------------------------------------------- */

/* s3w_ui_set_size: a size in px, or one of these. */
#define S3W_SIZE_CONTENT (-1) /* fit the content */
#define S3W_SIZE_FULL    (-2) /* 100 % of the parent's content area */

/* s3w_ui_list_add icons (0 = none). */
enum {
    S3W_ICON_NONE = 0,
    S3W_ICON_OK,
    S3W_ICON_CLOSE,
    S3W_ICON_PLUS,
    S3W_ICON_MINUS,
    S3W_ICON_PLAY,
    S3W_ICON_PAUSE,
    S3W_ICON_STOP,
    S3W_ICON_REFRESH,
    S3W_ICON_SETTINGS,
    S3W_ICON_HOME,
    S3W_ICON_BELL,
    S3W_ICON_EDIT,
    S3W_ICON_TRASH,
    S3W_ICON_LEFT,
    S3W_ICON_RIGHT,
    S3W_ICON_UP,
    S3W_ICON_DOWN,
    S3W_ICON_WARNING,
    S3W_ICON_LIST,
    S3W_ICON_COUNT
};

/* s3w_ui_set_style properties and their values. */
enum {
    S3W_STYLE_TEXT_COLOR = 1, /* 0xRRGGBB (on a button: its text) */
    S3W_STYLE_BG_COLOR,       /* 0xRRGGBB (also makes the background opaque) */
    S3W_STYLE_BG_OPA,         /* 0..255 */
    S3W_STYLE_FONT,           /* S3W_FONT_* (on a button: its text) */
    S3W_STYLE_RADIUS,         /* px, 0..255 */
    S3W_STYLE_ALIGN,          /* S3W_ALIGN_*: placement in the parent; s3w_ui_set_pos then offsets */
    S3W_STYLE_FLEX,           /* S3W_FLEX_*: lays out the children */
    S3W_STYLE_PAD,            /* inner padding, px, 0..255 */
    S3W_STYLE_GAP,            /* space between flex children, px, 0..255 */
    S3W_STYLE_TEXT_ALIGN,     /* S3W_TEXT_ALIGN_* */
};

enum { S3W_FONT_CAPTION = 0, S3W_FONT_BODY, S3W_FONT_TITLE, S3W_FONT_DISPLAY }; /* 22/26/32/96 px */

enum {
    S3W_ALIGN_TOP_LEFT = 0,
    S3W_ALIGN_TOP_MID,
    S3W_ALIGN_TOP_RIGHT,
    S3W_ALIGN_LEFT_MID,
    S3W_ALIGN_CENTER,
    S3W_ALIGN_RIGHT_MID,
    S3W_ALIGN_BOTTOM_LEFT,
    S3W_ALIGN_BOTTOM_MID,
    S3W_ALIGN_BOTTOM_RIGHT,
};

enum { S3W_FLEX_NONE = 0, S3W_FLEX_ROW, S3W_FLEX_COLUMN, S3W_FLEX_ROW_WRAP };

enum { S3W_TEXT_ALIGN_LEFT = 0, S3W_TEXT_ALIGN_CENTER, S3W_TEXT_ALIGN_RIGHT };

/* Display (410 x 502, rounded corners: keep text ~24 px in from the edges). */
#define S3W_SCREEN_W 410
#define S3W_SCREEN_H 502

/* --- Canvas mode constants ---------------------------------------------------------------- */

/* Canvas colours are RGB565: 5 bits red, 6 green, 5 blue. */
#define S3W_RGB565(r, g, b) ((uint16_t)((((r) & 0xF8) << 8) | (((g) & 0xFC) << 3) | (((b) & 0xFF) >> 3)))

#define S3W_GFX_FPS_DEFAULT 30
#define S3W_GFX_FPS_MAX     60

/* s3w_gfx_sprite flags. */
enum { S3W_SPRITE_FLIP_X = 1, S3W_SPRITE_FLIP_Y = 2 };

/* s3w_gfx_sprite_create: no transparent colour. */
#define S3W_SPRITE_NO_KEY (-1)

#define S3W_SPRITE_MAX       64           /* sprites per app */
#define S3W_SPRITE_MAX_BYTES (512 * 1024) /* all sprites' pixels together */

#if defined(__wasm__)

#define S3W_IMPORT(name) __attribute__((import_module("s3w"), import_name(#name)))
#define S3W_EXPORT(name) __attribute__((export_name(#name)))

/* --- Lifecycle: the app exports these (all optional) --------------------------------------- */
/* Build the UI, read saved state. 250 ms budget; a hang kills the app at once.
 * @since 1 */
void s3w_on_start(void) S3W_EXPORT(s3w_on_start);
/* The app is visible again. Must return within 250 ms (3 overruns kill the app).
 * @since 1 */
void s3w_on_resume(void) S3W_EXPORT(s3w_on_resume);
/* The app is covered or the screen is off. Must return within 250 ms (3 overruns kill the app).
 * @since 1 */
void s3w_on_pause(void) S3W_EXPORT(s3w_on_pause);
/* The system ends the app (not called after s3w_exit). Must return within 250 ms (3 overruns kill the app).
 * @since 1 */
void s3w_on_stop(void) S3W_EXPORT(s3w_on_stop);
/* One event (see S3W_EV_*); e is valid only during the call. Must return within 250 ms (3 overruns kill the app).
 * @since 1 */
void s3w_on_event(const s3w_event_t *e) S3W_EXPORT(s3w_on_event);

/* Canvas mode: called at the requested frame rate (s3w_gfx_set_fps) while the app is visible.
 * dt_ms is the time since the previous frame (0 for the first one after start or resume). Must return
 * within 250 ms (3 overruns kill the app).
 * @since 1 */
void s3w_on_frame(uint32_t dt_ms) S3W_EXPORT(s3w_on_frame);

/* Where the runtime writes the event it passes to s3w_on_event. Defined here (weak, so any
 * number of files may include this header); apps do not call it. @internal */
__attribute__((weak, export_name("s3w_event_buf"))) s3w_event_t *s3w_event_buf(void)
{
    static s3w_event_t ev;
    return &ev;
}

/* --- System ------------------------------------------------------------------------------- */
/* Milliseconds since the app started (monotonic).
 * @since 1 */
uint32_t s3w_millis(void) S3W_IMPORT(s3w_millis);
/* Seconds since 1970 (UTC), or 0 while the watch does not know the time.
 * @since 1 */
int64_t s3w_time_unix(void) S3W_IMPORT(s3w_time_unix);
/* Local time in the watch's time zone. S3W_ERR_NOT_READY while the time is unknown.
 * @since 1 */
int s3w_time_local(s3w_tm_t *out) S3W_IMPORT(s3w_time_local);
/* Writes msg (UTF-8, len bytes) to the app log at a level S3W_LOG_*; `s3w logs` shows it.
 * @since 1 */
void s3w_log(int level, const char *msg, int len) S3W_IMPORT(s3w_log);
/* Ends the app at once (s3w_on_stop is not called).
 * @since 1 */
void s3w_exit(void) S3W_IMPORT(s3w_exit);
/* Starts a timer (at least 20 ms, up to 8 at once): S3W_EV_TIMER with its id after each period.
 * Returns the id (> 0) or S3W_ERR_*.
 * @since 1 */
int s3w_timer_start(uint32_t period_ms, bool repeat) S3W_IMPORT(s3w_timer_start);
/* Stops a timer. An id that is not running (a one-shot that fired) is ignored.
 * @since 1 */
void s3w_timer_stop(int id) S3W_IMPORT(s3w_timer_stop);
/* Holds the screen on while the app is in the foreground (released when it ends).
 * @since 1  @perm keep_screen_on */
void s3w_keep_screen_on(bool on) S3W_IMPORT(s3w_keep_screen_on);
/* The UI language as a BCP 47 tag ("en", "de", "bn"), like snprintf: writes at most cap bytes
 * including a terminating NUL and returns the tag's length.
 * @since 1 */
int s3w_locale(char *buf, int cap) S3W_IMPORT(s3w_locale);

/* --- Widgets mode ------------------------------------------------------------------------- */
/* The app's full-screen root container (black, no padding, scrolls vertically if needed).
 * @since 1 */
int s3w_ui_screen(void) S3W_IMPORT(s3w_ui_screen);
/* A text label inside parent (a container handle). Returns its handle.
 * @since 1 */
int s3w_ui_label(int parent, const char *text, int len) S3W_IMPORT(s3w_ui_label);
/* Pill button: S3W_EV_CLICK.
 * @since 1 */
int s3w_ui_button(int parent, const char *text, int len) S3W_IMPORT(s3w_ui_button);
/* Full-size vertical list inset from the round corners.
 * @since 1 */
int s3w_ui_list(int parent) S3W_IMPORT(s3w_ui_list);
/* A tappable row (S3W_EV_CLICK with the row's handle); icon is S3W_ICON_*.
 * @since 1 */
int s3w_ui_list_add(int list, int icon, const char *text, int len) S3W_IMPORT(s3w_ui_list_add);
/* An image from the app's assets. S3W_ERR_NOT_FOUND for now: packages carry assets/, but loading them is not done yet.
 * @since 1 */
int s3w_ui_image(int parent, const char *asset_path, int len) S3W_IMPORT(s3w_ui_image);
/* A picture from the device's files (path as in s3w_fs_list): PNG, baseline JPEG or BMP (24 / 32 bit), reduced
 * to fit max_w x max_h px (1..S3W_FILE_IMAGE_MAX_SIDE; aspect kept, never enlarged). The watch decodes it
 * before returning, off the UI task: a PNG or BMP of up to S3W_FILE_IMAGE_MAX_PIXELS, a JPEG of up to
 * S3W_FILE_JPEG_MAX_PIXELS, a file of up to 3 MB, shrunk by at most 16 times; more is S3W_ERR_NO_RESOURCE.
 * S3W_ERR_NOT_FOUND (no such file), S3W_ERR_INVALID (path, size, progressive JPEG, damaged or another format),
 * S3W_ERR_DENIED (not a user place). Returns the widget.
 * @since 2  @perm files */
int s3w_ui_image_file(int parent, const char *path, int len, int max_w, int max_h) S3W_IMPORT(s3w_ui_image_file);
/* Progress ring (display only).
 * @since 1 */
int s3w_ui_arc(int parent, int min, int max, int value) S3W_IMPORT(s3w_ui_arc);
/* S3W_EV_VALUE while dragged.
 * @since 1 */
int s3w_ui_slider(int parent, int min, int max, int value) S3W_IMPORT(s3w_ui_slider);
/* S3W_EV_VALUE (0/1) when toggled.
 * @since 1 */
int s3w_ui_switch(int parent, bool on) S3W_IMPORT(s3w_ui_switch);
/* Label or button text.
 * @since 1 */
void s3w_ui_set_text(int h, const char *text, int len) S3W_IMPORT(s3w_ui_set_text);
/* Arc, slider (clamped to their range) or switch (0/1).
 * @since 1 */
void s3w_ui_set_value(int h, int v) S3W_IMPORT(s3w_ui_set_value);
/* Moves a widget to (x, y) px relative to its parent (an offset from its S3W_STYLE_ALIGN placement).
 * @since 1 */
void s3w_ui_set_pos(int h, int x, int y) S3W_IMPORT(s3w_ui_set_pos);
/* Buttons are at least 160 px wide until their size is set.
 * @since 1 */
void s3w_ui_set_size(int h, int w, int hgt) S3W_IMPORT(s3w_ui_set_size);
/* prop is S3W_STYLE_*; an unknown prop or bad value returns quietly (nothing changes).
 * @since 1 */
void s3w_ui_set_style(int h, int prop, int value) S3W_IMPORT(s3w_ui_set_style);
/* Deletes the widget and its children (their handles die too). Not the screen.
 * @since 1 */
void s3w_ui_delete(int h) S3W_IMPORT(s3w_ui_delete);
/* Shows a short message over the app for a moment.
 * @since 1 */
void s3w_ui_toast(const char *text, int len) S3W_IMPORT(s3w_ui_toast);
/* Confirm dialog over the app: S3W_EV_DIALOG with the returned id. One at a time.
 * @since 1 */
int s3w_ui_dialog(const char *title, int tl, const char *body, int bl, const char *ok, int ol)
    S3W_IMPORT(s3w_ui_dialog);

/* --- Canvas mode -------------------------------------------------------------------------- */
/* A 410 x 502 RGB565 canvas that keeps its pixels between frames: draw what changed, then call
 * s3w_gfx_present() once. Only the areas drawn since the last present reach the display (dirty
 * rectangles), so small changes are cheap. Coordinates are px from the top left; everything is
 * clipped to the canvas. The canvas starts black. */

/* Frames per second for s3w_on_frame, clamped to 1..S3W_GFX_FPS_MAX (default 30).
 * @since 1 */
void s3w_gfx_set_fps(int fps) S3W_IMPORT(s3w_gfx_set_fps);
/* Fills the whole canvas with color (RGB565, see S3W_RGB565).
 * @since 1 */
void s3w_gfx_clear(uint16_t color) S3W_IMPORT(s3w_gfx_clear);
/* Filled, or a 1 px outline.
 * @since 1 */
void s3w_gfx_rect(int x, int y, int w, int h, uint16_t color, bool fill) S3W_IMPORT(s3w_gfx_rect);
/* A circle of radius r around (cx, cy): filled, or a 1 px outline.
 * @since 1 */
void s3w_gfx_circle(int cx, int cy, int r, uint16_t color, bool fill) S3W_IMPORT(s3w_gfx_circle);
/* width 1..16 px.
 * @since 1 */
void s3w_gfx_line(int x0, int y0, int x1, int y1, uint16_t color, int width) S3W_IMPORT(s3w_gfx_line);
/* (x, y) is the top left of the first line; '\n' starts a new line. font is S3W_FONT_*. At most
 * 255 bytes of UTF-8.
 * @since 1 */
void s3w_gfx_text(int x, int y, const char *t, int len, int font, uint16_t color) S3W_IMPORT(s3w_gfx_text);
/* Width in px of one line of text in that font (for centring).
 * @since 1 */
int s3w_gfx_text_width(const char *t, int len, int font) S3W_IMPORT(s3w_gfx_text_width);
/* A sprite from RGB565 pixels in app memory (copied: the app may reuse its buffer). frames
 * frames of w x h px are stacked top to bottom (pixels holds w * h * frames values). key is the
 * transparent colour, or S3W_SPRITE_NO_KEY. Returns the sprite id (> 0) or S3W_ERR_INVALID (bad
 * size) / S3W_ERR_NO_RESOURCE (S3W_SPRITE_MAX or S3W_SPRITE_MAX_BYTES reached).
 * @since 1 */
int s3w_gfx_sprite_create(const uint16_t *pixels, int w, int h, int frames, int key)
    S3W_IMPORT(s3w_gfx_sprite_create);
/* A sprite from the app's assets. S3W_ERR_NOT_FOUND for now: packages carry assets/, but loading them is not done yet.
 * @since 1 */
int s3w_gfx_sprite_load(const char *asset, int len) S3W_IMPORT(s3w_gfx_sprite_load);
/* Draws frame (0-based) of sprite id with its top left at (x, y); flags S3W_SPRITE_FLIP_*.
 * An unknown id or a frame out of range traps.
 * @since 1 */
void s3w_gfx_sprite(int id, int x, int y, int frame, int flags) S3W_IMPORT(s3w_gfx_sprite);
/* Copies w x h RGB565 pixels (row by row) from app memory.
 * @since 1 */
void s3w_gfx_blit(const uint16_t *pixels, int x, int y, int w, int h) S3W_IMPORT(s3w_gfx_blit);
/* Ends the frame: what was drawn since the last present goes to the display once the current
 * callback returns.
 * @since 1 */
void s3w_gfx_present(void) S3W_IMPORT(s3w_gfx_present);

/* --- Sensors [perm: imu] ----------------------------------------------------------------- */
/* Streams the accelerometer as S3W_EV_IMU events at about rate_hz (1..100 asked; the sensor runs
 * at 62.5 Hz) while the app is visible. Returns the rate used. No gyroscope data yet.
 * @since 1  @perm imu */
int s3w_imu_start(int rate_hz) S3W_IMPORT(s3w_imu_start);
/* Stops the accelerometer stream.
 * @since 1  @perm imu */
void s3w_imu_stop(void) S3W_IMPORT(s3w_imu_stop);
/* Pitch and roll in degrees from the latest sample (0, 0 lying face up; pitch > 0: 12 o'clock
 * raised, roll > 0: 3 o'clock raised). Starts the accelerometer if no stream runs (no events
 * then): S3W_ERR_NOT_READY until it has a sample.
 * @since 1  @perm imu */
int s3w_tilt(float *pitch, float *roll) S3W_IMPORT(s3w_tilt);

/* --- Audio ------------------------------------------------------------------------------- */
/* volume is 0..100 of the watch's media volume in every audio function; Silent mutes. */
/* A tone, freq_hz 20..8000 for ms 1..10000 (replaces the app's tone if one plays).
 * @since 1  @perm audio.play */
int s3w_audio_tone(int freq_hz, int ms, int volume) S3W_IMPORT(s3w_audio_tone);
/* A WAV from the app's assets. S3W_ERR_NOT_FOUND for now: packages carry assets/, but loading them is not done yet.
 * @since 1  @perm audio.play */
int s3w_audio_play(const char *asset, int len, int volume) S3W_IMPORT(s3w_audio_play);
/* 16-bit mono PCM; sample_rate 16000 only (else S3W_ERR_UNSUPPORTED). One stream: returns its
 * handle. The volume is the media volume.
 * @since 1  @perm audio.play */
int s3w_audio_stream_open(int sample_rate) S3W_IMPORT(s3w_audio_stream_open);
/* Queues samples without waiting (the buffer holds 1 s); returns how many were taken.
 * @since 1  @perm audio.play */
int s3w_audio_stream_write(int h, const int16_t *pcm, int samples) S3W_IMPORT(s3w_audio_stream_write);
/* Stops a stream (its handle), or with 0 the app's tone and stream.
 * @since 1  @perm audio.play */
void s3w_audio_stop(int h) S3W_IMPORT(s3w_audio_stop);
/* Starts the microphone. S3W_ERR_UNSUPPORTED until the watch has voice support.
 * @since 1  @perm audio.record */
int s3w_mic_start(int sample_rate) S3W_IMPORT(s3w_mic_start);
/* Stops the microphone.
 * @since 1  @perm audio.record */
void s3w_mic_stop(void) S3W_IMPORT(s3w_mic_stop);

/* --- Storage ----------------------------------------------------------------------------- */
/* The app's own files: S3W_STORAGE_DEFAULT_KB in all, or the manifest's quota with the "storage"
 * permission (no permission needed). Keys and file names: 1..S3W_NAME_MAX bytes of
 * [A-Za-z0-9._-], not starting with '.' (S3W_ERR_INVALID otherwise). */
/* The value's length (copies at most cap bytes), or S3W_ERR_NOT_FOUND.
 * @since 1 */
int s3w_kv_get(const char *k, int kl, void *buf, int cap) S3W_IMPORT(s3w_kv_get);
/* vl ≤ S3W_KV_VALUE_MAX. S3W_ERR_NO_SPACE over the quota.
 * @since 1 */
int s3w_kv_set(const char *k, int kl, const void *v, int vl) S3W_IMPORT(s3w_kv_set);
/* Deletes a key. S3W_OK, or a negative S3W_ERR_* (S3W_ERR_INVALID for a bad key).
 * @since 1 */
int s3w_kv_delete(const char *k, int kl) S3W_IMPORT(s3w_kv_delete);
/* mode S3W_FILE_*: returns fd (≥ 1), S3W_ERR_NOT_FOUND (read), S3W_ERR_NO_RESOURCE (4 open).
 * @since 1 */
int s3w_file_open(const char *name, int len, int mode) S3W_IMPORT(s3w_file_open);
/* Bytes read (0 at the end) or written (S3W_ERR_NO_SPACE over the quota).
 * @since 1 */
int s3w_file_read(int fd, void *buf, int n) S3W_IMPORT(s3w_file_read);
/* Writes n bytes to a file opened with S3W_FILE_WRITE or S3W_FILE_APPEND. Returns the bytes written, or S3W_ERR_NO_SPACE over the quota.
 * @since 1 */
int s3w_file_write(int fd, const void *buf, int n) S3W_IMPORT(s3w_file_write);
/* Closes a file.
 * @since 1 */
void s3w_file_close(int fd) S3W_IMPORT(s3w_file_close);
/* Deletes one of the app's files. S3W_OK, or a negative S3W_ERR_* (S3W_ERR_NOT_FOUND if there is none).
 * @since 1 */
int s3w_file_delete(const char *name, int len) S3W_IMPORT(s3w_file_delete);

/* --- Device files [perm: files] (api_level 2) --------------------------------------------- */
/* The watch's own files, not the app's: the internal flash "/flash" and the card "/sd" (only while one is in).
 * Paths are absolute, '/'-separated, without "." or ".." parts, at most S3W_FS_PATH_MAX bytes. "/" lists the
 * roots. All of the card is open; of the flash only the user's data: /flash/memos, /flash/shots and
 * /flash/logs (everything else there is the system's: apps, keys, settings, stores). Other paths in /flash are
 * not listed and give S3W_ERR_DENIED. Names that start with '.' (temporary files) are not listed, and neither
 * is an entry whose name is longer than S3W_FS_NAME_MAX bytes. */
/* Lists a directory in name order (ASCII letters ignore their case; directories and files together): the
 * entries whose name sorts after `after` (al = 0: from the first), at most max of them. Paging: pass the last
 * name of a page to get the next, so the pages stay right while files come and go. Returns how many were
 * written (0 = past the end), S3W_ERR_NOT_FOUND (no such directory, or no card), S3W_ERR_DENIED,
 * S3W_ERR_INVALID (path, `after` longer than S3W_FS_NAME_MAX, max 1..32).
 * @since 2  @perm files */
int s3w_fs_list(const char *dir, int dl, const char *after, int al, s3w_fs_entry_t *out, int max)
    S3W_IMPORT(s3w_fs_list);
/* Deletes a file or an empty directory (one that holds only hidden files, which are not listed, counts as
 * empty and they go with it). S3W_ERR_NOT_FOUND, S3W_ERR_DENIED (not a user place, a root, or a directory with
 * anything else in it), S3W_ERR_IO.
 * @since 2  @perm files */
int s3w_fs_delete(const char *path, int len) S3W_IMPORT(s3w_fs_delete);
/* Opens a file for reading; one at a time (S3W_ERR_NO_RESOURCE while another is open). Returns the file's
 * size in bytes (a file over 2 GB: S3W_ERR_INVALID) or S3W_ERR_NOT_FOUND / S3W_ERR_DENIED. Closed with the
 * app.
 * @since 2  @perm files */
int s3w_fs_open(const char *path, int len) S3W_IMPORT(s3w_fs_open);
/* Bytes read from the open file (0 at the end), up to n (≤ 4096 per call). S3W_ERR_NOT_READY: none is open.
 * @since 2  @perm files */
int s3w_fs_read(void *buf, int n) S3W_IMPORT(s3w_fs_read);
/* Closes the file opened by s3w_fs_open (also done when the app ends).
 * @since 2  @perm files */
void s3w_fs_close(void) S3W_IMPORT(s3w_fs_close);

/* --- Game Boy core [perm: gameboy] (api_level 3, Pro edition) ------------------------------- */
/* A native emulator for DMG cartridge files on the card. The app passes the file's path, the
 * buttons and where to draw; the picture is drawn into the canvas by the firmware (canvas apps only).
 * ROMs must be on the card ("/sd/..."), anywhere else is S3W_ERR_DENIED. The cartridge RAM is kept next to
 * the ROM as "<name>.sav" (portable to PC emulators). One game at a time. */
/* Lists a folder of the card for the game library: like s3w_fs_list (name order, paging by the last name,
 * at most 32 entries per call), but only folders and cartridge files (.gb, .gbc, any case); anything else
 * is left out. The permission "gameboy" is enough: the app cannot see, read or delete other files.
 * S3W_ERR_DENIED outside "/sd", S3W_ERR_NOT_FOUND (no such folder, or no card).
 * @since 3  @perm gameboy */
int s3w_gb_list(const char *dir, int dl, const char *after, int al, s3w_fs_entry_t *out, int max)
    S3W_IMPORT(s3w_gb_list);
/* Reads the header of a cartridge file into `out`. S3W_OK; S3W_ERR_INVALID: damaged header, truncated file
 * (`out` is still filled when the header could be read); S3W_ERR_NOT_FOUND, S3W_ERR_DENIED (not on the
 * card), S3W_ERR_IO. Check `out->supported` before loading.
 * @since 3  @perm gameboy */
int s3w_gb_probe(const char *path, int len, s3w_gb_info_t *out) S3W_IMPORT(s3w_gb_probe);
/* Opens the cartridge and its save file and resets the console. S3W_ERR_UNSUPPORTED (mapper, colour-only
 * game), S3W_ERR_INVALID (damaged header, or a save of the wrong size, which is never overwritten),
 * S3W_ERR_NO_RESOURCE (a game is already loaded, or out of memory), S3W_ERR_IO.
 * @since 3  @perm gameboy */
int s3w_gb_load(const char *path, int len) S3W_IMPORT(s3w_gb_load);
/* Writes the cartridge RAM if it changed and closes the game (also done when the app ends).
 * S3W_ERR_NOT_READY: nothing loaded; S3W_ERR_IO: the save could not be written.
 * @since 3  @perm gameboy */
int s3w_gb_unload(void) S3W_IMPORT(s3w_gb_unload);
/* The buttons held now (S3W_GB_* or-ed together); stays until the next call.
 * @since 3  @perm gameboy */
void s3w_gb_input(uint32_t buttons) S3W_IMPORT(s3w_gb_input);
/* Runs the console for one video frame (1/59.7 s) and draws it with its top left at (x, y) of the canvas at
 * scale S3W_GB_SCALE_*: 160x144, 320x288 or 400x360 px. The whole picture must lie inside the canvas
 * (S3W_ERR_INVALID). Only the lines that changed since the last call that drew are written to the canvas
 * and marked as drawn (a still screen costs next to nothing); present as usual (s3w_gfx_present). After you
 * draw over the picture (a menu) pass S3W_GB_REDRAW; moving it, changing the scale or the palette redraws it
 * by itself. S3W_GB_NO_DRAW emulates the frame without drawing: when the display cannot keep up, run the
 * missed frames this way and draw only the last, so the game keeps its speed (the app paces: dt_ms of
 * s3w_on_frame / 16.74 ms per frame). Returns the milliseconds it took, S3W_ERR_NOT_READY (nothing loaded, or
 * drawing without a canvas), S3W_ERR_IO (the card failed mid-game: stop), S3W_ERR_UNSUPPORTED (the game did
 * something the core cannot do).
 * @since 3  @perm gameboy */
int s3w_gb_run_frame(int x, int y, int scale, uint32_t flags) S3W_IMPORT(s3w_gb_run_frame);
/* Writes the cartridge RAM now if it changed.
 * @since 3  @perm gameboy */
int s3w_gb_flush_ram(void) S3W_IMPORT(s3w_gb_flush_ram);
/* The four shades from lightest to darkest, RGB565 (default: white to black).
 * @since 3  @perm gameboy */
int s3w_gb_set_palette(const uint16_t *pal) S3W_IMPORT(s3w_gb_set_palette);
/* Save states: the whole console in "<game>.st<slot>" next to the ROM (slot 0..3; the card, not the flash).
 * s3w_gb_save_state writes it atomically; s3w_gb_load_state puts the console back (the next frame is drawn in
 * full). Errors: S3W_ERR_NOT_READY (nothing loaded), S3W_ERR_INVALID (slot, or a file that is not a state of this
 * game and this firmware's core, or damaged: the console is left as it was), S3W_ERR_NOT_FOUND (load: no such
 * state), S3W_ERR_IO. A state does not survive a firmware update that changes the core.
 * @since 3  @perm gameboy */
int s3w_gb_save_state(int slot) S3W_IMPORT(s3w_gb_save_state);
/* Puts the console back to the state saved in slot by s3w_gb_save_state; errors as there.
 * @since 3  @perm gameboy */
int s3w_gb_load_state(int slot) S3W_IMPORT(s3w_gb_load_state);
/* The console's sound: on = true opens the 16 kHz PCM stream (the one s3w_audio_stream_open uses: one at a time,
 * S3W_ERR_NO_RESOURCE while the app has its own open) and from then on every frame run by s3w_gb_run_frame, drawn
 * or not, adds its sound (mono, volume 0..100 of full); false closes it. Calling again with on = true only changes
 * the volume. Needs "audio.play" as well as "gameboy". Sound that is more than about 150 ms ahead of the speaker
 * is dropped, so the picture can fall behind without the sound lagging. Muted by the watch's Silent mode like any
 * stream. S3W_ERR_UNSUPPORTED: no audio on this watch. The sound registers follow the game whether or not sound is
 * on, and switching it on mid-game plays what is playing.
 * @since 3  @perm gameboy, audio.play */
int s3w_gb_set_audio(bool on, int volume) S3W_IMPORT(s3w_gb_set_audio);

/* --- Health [perm: health.read] ---------------------------------------------------------- */
/* Today's totals. S3W_ERR_UNSUPPORTED until the watch has activity tracking.
 * @since 1  @perm health.read */
int s3w_health_today(s3w_health_summary_t *out) S3W_IMPORT(s3w_health_today);

/* --- Network [perm: phone.http or wifi.http] --------------------------------------------- */
typedef struct {
    int32_t method;           /* S3W_HTTP_GET / S3W_HTTP_POST */
    const char *url;          /* http:// or https://, ≤ S3W_HTTP_URL_MAX bytes; its host must be */
    int32_t url_len;          /*   in the manifest's allowlist (S3W_ERR_DENIED otherwise) */
    const char *content_type; /* POST */
    int32_t content_type_len;
    const void *body;         /* POST, ≤ S3W_HTTP_BODY_MAX bytes */
    int32_t body_len;
    void *resp;               /* the response body goes here: keep it until S3W_EV_HTTP */
    int32_t resp_cap;         /* 0..S3W_HTTP_RESP_MAX */
} s3w_http_req_t;             /* 36 bytes */
/* Through the phone (Wi-Fi comes later). Returns the request id (S3W_EV_HTTP follows),
 * S3W_ERR_NOT_READY (no phone), S3W_ERR_NO_RESOURCE (S3W_HTTP_MAX running).
 * @since 1  @perm phone.http or wifi.http */
int s3w_http_request(const s3w_http_req_t *req) S3W_IMPORT(s3w_http_request);

/* --- Notifications [perm: notify] -------------------------------------------------------- */
/* A notification from the app (at most one every 10 s: S3W_ERR_NO_RESOURCE).
 * @since 1  @perm notify */
int s3w_notify(const char *title, int tl, const char *body, int bl) S3W_IMPORT(s3w_notify);

/* --- Game services ----------------------------------------------------------------------- */
/* Records score on board (0..S3W_HIGHSCORE_BOARDS - 1) if it beats the best: higher wins, or
 * lower with S3W_HIGHSCORE_LOWER (times). Kept in the app's storage (not counted in its quota),
 * so it survives restarts and updates. Returns 1 for a new best, 0 if not, or S3W_ERR_*.
 * @since 1 */
int s3w_highscore_submit(int board, int score) S3W_IMPORT(s3w_highscore_submit);
/* The board's best: S3W_OK with *best, or S3W_ERR_NOT_FOUND before the first score.
 * @since 1 */
int s3w_highscore_get(int board, int *best) S3W_IMPORT(s3w_highscore_get);
/* A random number 0..0x7FFFFFFF (the watch's hardware RNG).
 * @since 1 */
int s3w_random(void) S3W_IMPORT(s3w_random);

#endif /* __wasm__ */

#ifdef __cplusplus
}
#endif

#endif /* S3W_H */
