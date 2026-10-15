# Canvas mode

A 410 x 502 RGB565 canvas that keeps its pixels between frames: draw what changed, then call [`s3w_gfx_present`](#s3w_gfx_present)() once. Only the areas drawn since the last present reach the display (dirty rectangles), so small changes are cheap. Coordinates are px from the top left; everything is clipped to the canvas. The canvas starts black.

## s3w_gfx_set_fps

```c
void s3w_gfx_set_fps(int fps);
```

_api_level 1_

Frames per second for [`s3w_on_frame`](lifecycle.md#s3w_on_frame), clamped to 1..`S3W_GFX_FPS_MAX` (default 30).

## s3w_gfx_clear

```c
void s3w_gfx_clear(uint16_t color);
```

_api_level 1_

Fills the whole canvas with color (RGB565, see `S3W_RGB565`).

## s3w_gfx_rect

```c
void s3w_gfx_rect(int x, int y, int w, int h, uint16_t color, bool fill);
```

_api_level 1_

Filled, or a 1 px outline.

## s3w_gfx_circle

```c
void s3w_gfx_circle(int cx, int cy, int r, uint16_t color, bool fill);
```

_api_level 1_

A circle of radius r around (cx, cy): filled, or a 1 px outline.

## s3w_gfx_line

```c
void s3w_gfx_line(int x0, int y0, int x1, int y1, uint16_t color, int width);
```

_api_level 1_

width 1..16 px.

## s3w_gfx_text

```c
void s3w_gfx_text(int x, int y, const char *t, int len, int font, uint16_t color);
```

_api_level 1_

(x, y) is the top left of the first line; '\\n' starts a new line. font is `S3W_FONT_*`. At most 255 bytes of UTF-8.

## s3w_gfx_text_width

```c
int s3w_gfx_text_width(const char *t, int len, int font);
```

_api_level 1_

Width in px of one line of text in that font (for centring).

## s3w_gfx_sprite_create

```c
int s3w_gfx_sprite_create(const uint16_t *pixels, int w, int h, int frames, int key);
```

_api_level 1_

A sprite from RGB565 pixels in app memory (copied: the app may reuse its buffer). frames frames of w x h px are stacked top to bottom (pixels holds w \* h \* frames values). key is the transparent colour, or `S3W_SPRITE_NO_KEY`. Returns the sprite id (&gt; 0) or `S3W_ERR_INVALID` (bad size) / `S3W_ERR_NO_RESOURCE` (`S3W_SPRITE_MAX` or `S3W_SPRITE_MAX_BYTES` reached).

## s3w_gfx_sprite_load

```c
int s3w_gfx_sprite_load(const char *asset, int len);
```

_api_level 1_

A sprite from the app's assets. `S3W_ERR_NOT_FOUND` for now: packages carry assets/, but loading them is not done yet.

## s3w_gfx_sprite

```c
void s3w_gfx_sprite(int id, int x, int y, int frame, int flags);
```

_api_level 1_

Draws frame (0-based) of sprite id with its top left at (x, y); flags `S3W_SPRITE_FLIP_*`. An unknown id or a frame out of range traps.

## s3w_gfx_blit

```c
void s3w_gfx_blit(const uint16_t *pixels, int x, int y, int w, int h);
```

_api_level 1_

Copies w x h RGB565 pixels (row by row) from app memory.

## s3w_gfx_present

```c
void s3w_gfx_present(void);
```

_api_level 1_

Ends the frame: what was drawn since the last present goes to the display once the current callback returns.
