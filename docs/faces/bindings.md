# Bindings

A binding is a name for a value the watch has. `"bind": "battery.percent"` makes a text show the battery level, and an
arc or hand can use the numeric form. Faces cannot run code; this is the whole vocabulary.

The complete, current list is generated from the watch's own registry: [the face registry](../api/faces.md#bindings).
Each binding has a **text** form (what a `text` element shows), a **value** form (a number for an `arc` or `hand`), or
both, and says which data change makes it redraw.

| Family | Examples | Notes |
|---|---|---|
| Time | `time.hh:mm`, `time.hh`, `time.mm`, `time.ss`, `time.ampm` | 12 or 24 hours as the user set. `--:--` while the time is not set |
| Hand angles | `time.hour`, `time.minute`, `time.second` | Value only: tenths of a degree clockwise from 12 |
| Date | `date.<pattern>` | A pattern such as `date.EEE d MMM` ("Sat 3 Oct"); see below |
| Battery | `battery.percent`, `battery.ratio`, `battery.charging` | `ratio` is 0 to 1000 |
| Steps | `steps.count`, `steps.goal`, `steps.goal_ratio` | `goal_ratio` is capped at 1000 |
| Weather | `weather.temp`, `.low`, `.high`, `.condition` | From the phone; unknown shows `--` |
| Phone | `phone.battery` | |
| Calendar | `next_event.title`, `next_event.time` | |
| Other | `heart.bpm`, `notifications.count`, `moon.phase`, `moon.illumination` | |

When the data is unknown, a text shows `--` (or `--:--`) and a numeric binding has no value, so a gauge stays empty.

## Date patterns

`date.<pattern>`: `EEEE` (Saturday), `EEE` (Sat), `d` (3), `dd` (03), `MMMM` (October), `MMM` (Oct), `MM` (10), `M` (10),
`yyyy` (2026), `yy` (26). Letters outside these are an error; anything else is copied (`date.EEE d MMM`, `date.d/M`).
The names are English for now. A pattern is at most 23 characters.

## Using the numeric form

```
{"type": "arc", "bind": "battery.ratio", "x": 205, "y": 251, "r": 190, "w": 8, "start": 135, "end": 405, "color": "accent"}
{"type": "hand", "bind": "time.minute", "len": 160, "w": 8}
```

A binding without a numeric form (like `next_event.title`) in an `arc` or `hand` is an error at build time
(`bind: 'next_event.title' has no numeric form`), and so is a `text` that binds to a hand angle (`has no text form`).
