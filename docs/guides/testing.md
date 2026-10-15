# Testing with simulator scripts

A **script** is a text file of commands the simulator runs headless: tap, swipe, wait, set the accelerometer, answer an
HTTP request, then check the state. It exits non-zero if a check fails, so a script is a test.

```
# bounce.txt: the ball falls; two taps keep it in the air
wait 600
tap 205 300
wait 300
tap 205 300
wait 300
app-is running
app-frames 10
```

```bash
s3w run-sim bounce --script bounce.txt --screenshot out.png
echo $?        # 0: every check passed
```

| Check | Fails unless |
|---|---|
| `app-is running` | The app is still running (not `exited`, `trapped` or `hung`) |
| `app-frames <n>` | A canvas app has run n frames (a widgets app: n frame periods of 1/30 s of run time) |
| `app-installed <id> <version>` | That version is installed |

Useful inputs: `tap x y`, `swipe x1 y1 x2 y2`, `hold x y ms`, `imu x y z`, `app-http 200 body`, `app-button down`,
`wait ms`, `time HH:MM`. The full list is in [simulator scripts](../reference/simulator-scripts.md).

## What a script should cover

- **Start and run**: `app-is running` after a few hundred frames proves the app does not trap or hang.
- **The path a user takes**: taps through the main screens, then a screenshot to look at.
- **The error paths**: `app-http error` for a failed request, a missing permission by deleting it from the manifest.

The store's own automated checks go further ([publish](../publish/index.md)); a script of your own is where to start.
