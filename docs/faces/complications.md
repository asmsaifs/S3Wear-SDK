# Complications

A complication is a small piece of information in a slot: battery, steps, next event. The user can change what a slot
shows from the face's customise screen; your face chooses where the slots are and what they show by default.

```
{"type": "complication", "slot": "bottom", "x": 205, "y": 410, "style": "circle", "default": "battery"}
```

- `slot` names the slot; use a short name and keep it the same across versions so the user's choice survives an update.
- `style` is `circle` (a gauge ring around a value and a caption) or `line` (a wide slot with a longer detail text).
- `default` is a complication id from the list below.
- At most 4 slots in a face, and none in the `aod` layout.

The ids, their names and the app a tap opens are generated from the watch: [the face registry](../api/faces.md#complications).
A complication that has no data yet shows `--`.

A face with no complications is allowed; so is one made only of complications. They are the part of a face that is
the user's, so do not hide one behind another element.
