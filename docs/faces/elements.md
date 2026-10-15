# Elements

Each element has a `"type"`. `*` marks a required field; the value in brackets is the default.

| Type | Fields |
|---|---|
| `text` | `bind`* or `text`*, `x`*, `y`*, `font` (`body_26`), `color` (`#FFFFFF`), `align` (`center`, `left`, `right`), `upper` (false) |
| `arc` | `bind`* (numeric), `r`*, `x`, `y` (the centre), `w` (8), `start` (135), `end` (405), `max` (1000), `color` (`accent`), `track` (none), `rounded` (true) |
| `hand` | `bind`* (numeric), `x`, `y` (pivot, the centre), `len` (150), `tail` (0), `w` (4), `color` (`#FFFFFF`), `image`, `pivot` |
| `circle` | `x`*, `y`*, `r`*, `w` (0 is filled, else the ring width), `color` (`#FFFFFF`) |
| `rect` | `x`*, `y`*, `w`*, `h`*, `radius` (0), `color` (`#FFFFFF`) |
| `ticks` | `r`* (outer), `count`*, `x`, `y`, `len` (10), `w` (2), `color` (`#9A9AA0`), `major` (every n-th tick, 0 none), `major_len`, `major_w`, `major_color` |
| `image` | `image`* (a PNG file name), `x`*, `y`* (the centre; see [images](images.md)) |
| `complication` | `slot`* (an id), `x`*, `y`*, `style` (`circle` or `line`), `default` (none) |

## text

Shows a binding's text (`"bind": "time.hh:mm"`) or fixed text (`"text": "steps"`, at most 32 characters). `upper`
turns it to capitals. Digits-only fonts (`digits_*`) draw digits and `: . , - + %` only.

## arc

A ring that fills in proportion to a binding's number: `value / max` of the way from `start` to `end`. Angles are degrees
clockwise from 3 o'clock; `end - start` must be 1 to 360. `steps.goal_ratio` is 0 to 1000, so the default `max` of 1000
fits it. A `track` colour draws the empty part.

## hand

A clock hand driven by a binding that gives an angle: `time.hour`, `time.minute` and `time.second` are angles in tenths
of a degree clockwise from 12. `len` is the length from the pivot, `tail` the part behind it. Hands turn about `(x, y)`.
With `image` (and optionally `pivot`) the hand is a picture instead of a line: see [images](images.md).

## circle, rect, ticks

Plain shapes. A `ticks` element draws `count` marks on a circle of radius `r`; with `major` every n-th mark is longer,
thicker and may have its own colour: `{"type":"ticks","r":196,"count":60,"len":8,"w":2,"major":5,"major_len":20,"major_w":6}`
is a classic minute track.

## complication

A slot the user can fill. `slot` is your name for it (up to 16 characters, `center`, `bottom`, ...), `style` is how it is
drawn (`circle` with a gauge, or `line` for a wide slot), `default` is the [complication](complications.md) shown until
the user picks another. At most 4 slots. A tap opens the complication's app. Complications are not allowed in `aod`.

## Order

Elements are drawn in the order of the array: put the background shapes first and the hands last.
