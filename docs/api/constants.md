# Constants and types

Everything the header defines apart from the functions: error codes, events, structs and limits. The header is
the reference; this page shows it as written.

```c
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
```
