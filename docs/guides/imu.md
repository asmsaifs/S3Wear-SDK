# IMU and tilt

The accelerometer needs the `imu` [permission](../concepts/permissions.md). There are two ways to read it.

**Tilt**: `s3w_tilt(&pitch, &roll)` gives angles in degrees from the latest sample: 0, 0 lying face up; pitch above 0
when 12 o'clock is raised, roll above 0 when 3 o'clock is raised. It starts the sensor itself if no stream runs, and
returns `S3W_ERR_NOT_READY` until it has a sample. Good for a spirit level or steering.

**Stream**: `s3w_imu_start(rate_hz)` sends `S3W_EV_IMU` events while the app is visible: `x`, `y`, `value` are the
acceleration along the watch's axes in milli-g (+x towards 3 o'clock, +y towards 12, +z out of the screen) and `handle`
is the number of samples the event stands for, because newer samples replace older ones while the app is busy. The sensor
runs at 62.5 Hz at most; you are told the rate used. There is no gyroscope data.

```c-check
#include "s3w.h"

static int s_x = S3W_SCREEN_W / 2;
static int s_y = S3W_SCREEN_H / 2;

void s3w_on_start(void)
{
    s3w_imu_start(50);
    s3w_gfx_set_fps(30);
}

void s3w_on_stop(void)
{
    s3w_imu_stop();
}

void s3w_on_frame(uint32_t dt_ms)
{
    float pitch = 0, roll = 0;
    if (s3w_tilt(&pitch, &roll) == S3W_OK) {
        /* the ball rolls to the low side: tilt towards 3 o'clock moves it right */
        s_x += (int)(roll * 0.3f * (float)dt_ms / 16.0f);
        s_y -= (int)(pitch * 0.3f * (float)dt_ms / 16.0f);
        s_x = s_x < 20 ? 20 : s_x > S3W_SCREEN_W - 20 ? S3W_SCREEN_W - 20 : s_x;
        s_y = s_y < 20 ? 20 : s_y > S3W_SCREEN_H - 20 ? S3W_SCREEN_H - 20 : s_y;
    }
    s3w_gfx_clear(S3W_RGB565(0, 0, 0));
    s3w_gfx_circle(s_x, s_y, 20, S3W_RGB565(255, 214, 10), true);
    s3w_gfx_present();
}
```

In the simulator, the script command `imu x y z` sets the acceleration apps read (`imu 0 0 1000` is lying flat);
`imu 300 0 950` tilts it. See [simulator scripts](../reference/simulator-scripts.md).

In a game loop, integer maths on the milli-g values is cheaper than floats in the watch's interpreter.
