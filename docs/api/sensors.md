# Sensors

## s3w_imu_start

```c
int s3w_imu_start(int rate_hz);
```

_api_level 1 · permission `imu`_

Streams the accelerometer as `S3W_EV_IMU` events at about rate_hz (1..100 asked; the sensor runs at 62.5 Hz) while the app is visible. Returns the rate used. No gyroscope data yet.

## s3w_imu_stop

```c
void s3w_imu_stop(void);
```

_api_level 1 · permission `imu`_

Stops the accelerometer stream.

## s3w_tilt

```c
int s3w_tilt(float *pitch, float *roll);
```

_api_level 1 · permission `imu`_

Pitch and roll in degrees from the latest sample (0, 0 lying face up; pitch &gt; 0: 12 o'clock raised, roll &gt; 0: 3 o'clock raised). Starts the accelerometer if no stream runs (no events then): `S3W_ERR_NOT_READY` until it has a sample.
