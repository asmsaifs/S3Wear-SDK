# face.json

The format is described across the [faces section](../faces/overview.md); this page is the summary. Level (`api`): 1.

```json
{
  "id": "dev.you.example",
  "name": "Example",
  "version": "1.0.0",
  "api": 1,
  "author": "You",
  "description": "Optional text.",
  "background": "#000000",
  "elements": [ { "type": "text", "bind": "time.hh:mm", "x": 205, "y": 251, "font": "digits_96" } ],
  "aod": { "elements": [ { "type": "text", "bind": "time.hh:mm", "x": 205, "y": 251, "font": "digits_96_light" } ] }
}
```

| Page | Content |
|---|---|
| [Overview](../faces/overview.md) | Top-level keys, the screen, colours |
| [Elements](../faces/elements.md) | `text`, `arc`, `hand`, `circle`, `rect`, `ticks`, `image`, `complication` and their fields |
| [Bindings](../faces/bindings.md), [registry](../api/faces.md) | Every binding, font and complication the watch knows |
| [AOD](../faces/aod.md) | The always-on layout |
| [Limits](../faces/limits.md) | Sizes, counts, the package |

Check a file with the watch's own parser: `s3w_sim --check-face face.json` prints the id, name, version, api and image
list as JSON, or `face.json:LINE:COL: reason` and exit status 1.
