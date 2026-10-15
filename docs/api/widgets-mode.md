# Widgets mode

## s3w_ui_screen

```c
int s3w_ui_screen(void);
```

_api_level 1_

The app's full-screen root container (black, no padding, scrolls vertically if needed).

## s3w_ui_label

```c
int s3w_ui_label(int parent, const char *text, int len);
```

_api_level 1_

A text label inside parent (a container handle). Returns its handle.

## s3w_ui_button

```c
int s3w_ui_button(int parent, const char *text, int len);
```

_api_level 1_

Pill button: `S3W_EV_CLICK`.

## s3w_ui_list

```c
int s3w_ui_list(int parent);
```

_api_level 1_

Full-size vertical list inset from the round corners.

## s3w_ui_list_add

```c
int s3w_ui_list_add(int list, int icon, const char *text, int len);
```

_api_level 1_

A tappable row (`S3W_EV_CLICK` with the row's handle); icon is `S3W_ICON_*`.

## s3w_ui_image

```c
int s3w_ui_image(int parent, const char *asset_path, int len);
```

_api_level 1_

An image from the app's assets. `S3W_ERR_NOT_FOUND` for now: packages carry assets/, but loading them is not done yet.

## s3w_ui_image_file

```c
int s3w_ui_image_file(int parent, const char *path, int len, int max_w, int max_h);
```

_api_level 2 · permission `files`_

A picture from the device's files (path as in [`s3w_fs_list`](device-files.md#s3w_fs_list)): PNG, baseline JPEG or BMP (24 / 32 bit), reduced to fit max_w x max_h px (1..`S3W_FILE_IMAGE_MAX_SIDE`; aspect kept, never enlarged). The watch decodes it before returning, off the UI task: a PNG or BMP of up to `S3W_FILE_IMAGE_MAX_PIXELS`, a JPEG of up to `S3W_FILE_JPEG_MAX_PIXELS`, a file of up to 3 MB, shrunk by at most 16 times; more is `S3W_ERR_NO_RESOURCE`. `S3W_ERR_NOT_FOUND` (no such file), `S3W_ERR_INVALID` (path, size, progressive JPEG, damaged or another format), `S3W_ERR_DENIED` (not a user place). Returns the widget.

## s3w_ui_arc

```c
int s3w_ui_arc(int parent, int min, int max, int value);
```

_api_level 1_

Progress ring (display only).

## s3w_ui_slider

```c
int s3w_ui_slider(int parent, int min, int max, int value);
```

_api_level 1_

`S3W_EV_VALUE` while dragged.

## s3w_ui_switch

```c
int s3w_ui_switch(int parent, bool on);
```

_api_level 1_

`S3W_EV_VALUE` (0/1) when toggled.

## s3w_ui_set_text

```c
void s3w_ui_set_text(int h, const char *text, int len);
```

_api_level 1_

Label or button text.

## s3w_ui_set_value

```c
void s3w_ui_set_value(int h, int v);
```

_api_level 1_

Arc, slider (clamped to their range) or switch (0/1).

## s3w_ui_set_pos

```c
void s3w_ui_set_pos(int h, int x, int y);
```

_api_level 1_

Moves a widget to (x, y) px relative to its parent (an offset from its `S3W_STYLE_ALIGN` placement).

## s3w_ui_set_size

```c
void s3w_ui_set_size(int h, int w, int hgt);
```

_api_level 1_

Buttons are at least 160 px wide until their size is set.

## s3w_ui_set_style

```c
void s3w_ui_set_style(int h, int prop, int value);
```

_api_level 1_

prop is `S3W_STYLE_*`; an unknown prop or bad value returns quietly (nothing changes).

## s3w_ui_delete

```c
void s3w_ui_delete(int h);
```

_api_level 1_

Deletes the widget and its children (their handles die too). Not the screen.

## s3w_ui_toast

```c
void s3w_ui_toast(const char *text, int len);
```

_api_level 1_

Shows a short message over the app for a moment.

## s3w_ui_dialog

```c
int s3w_ui_dialog(const char *title, int tl, const char *body, int bl, const char *ok, int ol);
```

_api_level 1_

Confirm dialog over the app: `S3W_EV_DIALOG` with the returned id. One at a time.
