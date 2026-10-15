# Icons and screenshots

## The icon

Put `icon.png` next to `manifest.json`. The launcher shows it, and the store does too.

- 80 × 80 pixels, PNG, 8 bits per channel (grey, RGB, palette, grey + alpha or RGBA), not interlaced, at most 64 KB.
- Round with transparent corners reads best on the watch's launcher; keep the picture inside about 70 px.
- `s3w build` checks these rules, and the watch refuses an icon that does not decode.

Without an icon the launcher shows the first letter of the app's name on a coloured disc.

## Screenshots from the simulator

The simulator can take a picture headless, from a script of taps and waits. The clock is pinned (10:09) and nothing
random changes, so the same script gives the same image every time.

```bash
s3w run-sim my-app --script shot.txt --screenshot shot.png
```

with `shot.txt` such as:

```
wait 600            # let the app start
tap 205 300         # press something
wait 400
```

The picture is the last frame. [Simulator scripts](../reference/simulator-scripts.md) lists the commands. Store listings
use screenshots made this way, so a script is the way to keep them current when your UI changes. Screenshots are 410 × 502.

## Tips

- Take screenshots in the state a user would find interesting: a game mid-play, a list with data, not the empty start.
- Use `app-http`, `imu` and `time` to put the app in that state without a phone.
- Check both the widgets rendering and any text near the rounded corners.
