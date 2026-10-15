# Building UIs with widgets

A widgets app (`"ui_mode": "widgets"`) builds a tree of widgets from the screen container. Every function returns a
**handle**; pass it to change or delete the widget. A handle that is not live (deleted, never made, wrong kind) stops
the app, so keep handles in variables and do not use one after `s3w_ui_delete`.

| Widget | Make with | Event |
|---|---|---|
| Label | `s3w_ui_label(parent, text, len)` | none |
| Button | `s3w_ui_button` | `S3W_EV_CLICK` (handle) |
| List and rows | `s3w_ui_list`, `s3w_ui_list_add(list, icon, text, len)` | `S3W_EV_CLICK` (the row's handle) |
| Slider | `s3w_ui_slider(parent, min, max, value)` | `S3W_EV_VALUE` while dragged |
| Switch | `s3w_ui_switch(parent, on)` | `S3W_EV_VALUE` (0 or 1) |
| Progress ring | `s3w_ui_arc(parent, min, max, value)` | none (display only) |
| Toast, dialog | `s3w_ui_toast`, `s3w_ui_dialog` | dialog: `S3W_EV_DIALOG` (1 ok, 0 cancelled) |

```c-check
#include "s3w.h"

#define STR(s) s, (int)(sizeof(s) - 1)

static int s_list, s_slider, s_switch;
static int s_level_label;

void s3w_on_start(void)
{
    const int screen = s3w_ui_screen();
    s3w_ui_set_style(screen, S3W_STYLE_FLEX, S3W_FLEX_COLUMN);
    s3w_ui_set_style(screen, S3W_STYLE_PAD, 36);
    s3w_ui_set_style(screen, S3W_STYLE_GAP, 12);

    const int title = s3w_ui_label(screen, STR("Settings"));
    s3w_ui_set_style(title, S3W_STYLE_FONT, S3W_FONT_TITLE);
    s3w_ui_set_style(title, S3W_STYLE_TEXT_COLOR, 0xFFD60A);

    s_level_label = s3w_ui_label(screen, STR("Level 5"));
    s_slider = s3w_ui_slider(screen, 0, 10, 5);
    s3w_ui_set_size(s_slider, S3W_SIZE_FULL, S3W_SIZE_CONTENT);
    s_switch = s3w_ui_switch(screen, true);

    s_list = s3w_ui_list(screen);
    s3w_ui_list_add(s_list, S3W_ICON_SETTINGS, STR("Advanced"));
    s3w_ui_list_add(s_list, S3W_ICON_TRASH, STR("Reset everything"));
}

void s3w_on_event(const s3w_event_t *e)
{
    if (e->type == S3W_EV_VALUE && e->handle == s_slider) {
        char t[] = "Level 0";
        t[6] = (char)('0' + e->value % 10);
        s3w_ui_set_text(s_level_label, t, 7);
    } else if (e->type == S3W_EV_VALUE && e->handle == s_switch) {
        s3w_ui_toast(e->value ? "On" : "Off", e->value ? 2 : 3);
    } else if (e->type == S3W_EV_CLICK) {
        s3w_ui_dialog(STR("Reset"), STR("Delete all data?"), STR("Delete"));
    }
}
```

## Layout

`s3w_ui_screen()` is a black, full-screen container without padding that scrolls vertically if its content is taller.
Two ways to place children:

- **Flex**: `s3w_ui_set_style(parent, S3W_STYLE_FLEX, S3W_FLEX_COLUMN)` (or `ROW`, `ROW_WRAP`) lays the children out
  in order; `S3W_STYLE_GAP` is the space between them and `S3W_STYLE_PAD` the padding inside.
- **Alignment and position**: `S3W_STYLE_ALIGN` places a widget inside its parent (`S3W_ALIGN_CENTER`,
  `S3W_ALIGN_TOP_MID`, ...) and `s3w_ui_set_pos(h, x, y)` then offsets it.

`s3w_ui_set_size(h, w, h)` takes px, `S3W_SIZE_CONTENT` or `S3W_SIZE_FULL`. Buttons are at least 160 px wide until you
set a width.

The display is 410 × 502 with rounded corners: keep text about 24 px in from the edges. Lists are already inset.

## Styling

`s3w_ui_set_style(h, prop, value)` takes a small whitelist: `S3W_STYLE_TEXT_COLOR` and `S3W_STYLE_BG_COLOR`
(`0xRRGGBB`), `S3W_STYLE_BG_OPA` (0 to 255), `S3W_STYLE_FONT` (`S3W_FONT_CAPTION` 22 px, `BODY` 26, `TITLE` 32,
`DISPLAY` 96), `S3W_STYLE_RADIUS`, `S3W_STYLE_ALIGN`, `S3W_STYLE_FLEX`, `S3W_STYLE_PAD`, `S3W_STYLE_GAP`,
`S3W_STYLE_TEXT_ALIGN`. An unknown property or a bad value changes nothing and does not stop the app.

## Good habits

- Update text only when it changes.
- Build the screen in `s3w_on_start`. Change it from `s3w_on_event`.
- The system's back gesture and the PWR button leave the app; do not draw your own back button for that.

Pictures: `s3w_ui_image` loads from the package's `assets/` and returns `S3W_ERR_NOT_FOUND` for now. A picture from the
user's files can be shown with `s3w_ui_image_file` (permission `files`).
