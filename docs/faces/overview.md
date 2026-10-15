# Watch faces: format overview

A face is a folder with a `face.json` and, if it uses them, image files. `s3w face build <dir>` checks it with the
watch's own parser, renders a preview and packs `build/<id>.s3face`.

```face-check
{
  "id": "dev.you.minimal",
  "name": "Minimal",
  "version": "1.0.0",
  "api": 1,
  "background": "#000000",
  "elements": [
    {"type": "text", "bind": "time.hh:mm", "x": 205, "y": 251, "font": "digits_96", "color": "#FFFFFF"}
  ]
}
```

## Top level

| Key | Meaning |
|---|---|
| `id` | Lower case letters, digits, `.`, `_`, `-`; 1 to 47 characters; not starting with `.`. Built-in ids (`digital`, `analog`, `modular`, `minimal`) and `s3w.*` are taken |
| `name` | Shown in the picker, at most 32 characters |
| `version` | `MAJOR.MINOR.PATCH`. An update must not be older |
| `api` | The face format level; the current one is 1. The watch refuses a face with a higher level than it has |
| `author`, `description` | Optional |
| `background` | A colour (`"#RRGGBB"`) or an image file name |
| `elements` | 1 to 32 elements, drawn in order |
| `aod` | Optional: the always-on layout, see [AOD](aod.md) |

Every key the parser does not know is an **error**, not ignored: a typo in a key name is caught at build time. So are
wrong types, values out of range, unknown bindings, fonts and complications, and duplicate keys.

## The screen

The face has the whole 410 × 502 screen. Every element is placed by its **centre** `(x, y)`. A text's `x` is its left,
centre or right edge according to `align`, and its `y` the middle of the line. The corners are rounded: keep important
things inside the display's safe area.

## Colours

`"#RRGGBB"`, or `"accent"` for the colour the user picked in the settings.

## What is where

[Elements](elements.md) are what you draw. [Bindings](bindings.md) are the values they show. [Fonts](fonts.md),
[complications](complications.md) and the [always-on layout](aod.md) have their own pages; [images](images.md),
the [preview](preview.md) and the [limits](limits.md) close the section.

The picker, the colour customisation and the complication slots are the watch's: your face only declares the slots.
