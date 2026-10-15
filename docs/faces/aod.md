# The always-on layout

When the display is dimmed in its always-on mode, the watch draws the face's **AOD layout**: black background, very few
lit pixels (the watch's own faces stay under 10 percent), and the content shifts a few pixels each minute so no pixel
burns in.

```
"aod": {
  "elements": [
    {"type": "text", "bind": "time.hh:mm", "x": 205, "y": 251, "font": "digits_96_light", "color": "#6E6E73"}
  ]
}
```

- Up to 8 elements; the types are the same as in the main layout.
- **No complications** in the AOD layout.
- The background is always black; do not rely on a coloured one.
- A hand of the main face can be repeated here thinner and dimmer.

Without an `aod` key the watch shows the time in `digits_96_light`, dim grey, centred.

In the simulator, a script can show the AOD layout with `aod on` and check how much is lit with `lit 10`
([simulator scripts](../reference/simulator-scripts.md)).
