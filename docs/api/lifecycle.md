# Lifecycle

_The app exports these (all optional)_

## s3w_on_start

```c
void s3w_on_start(void);
```

_api_level 1 · callback the app exports_

Build the UI, read saved state. 250 ms budget; a hang kills the app at once.

## s3w_on_resume

```c
void s3w_on_resume(void);
```

_api_level 1 · callback the app exports_

The app is visible again. Must return within 250 ms (3 overruns kill the app).

## s3w_on_pause

```c
void s3w_on_pause(void);
```

_api_level 1 · callback the app exports_

The app is covered or the screen is off. Must return within 250 ms (3 overruns kill the app).

## s3w_on_stop

```c
void s3w_on_stop(void);
```

_api_level 1 · callback the app exports_

The system ends the app (not called after [`s3w_exit`](system.md#s3w_exit)). Must return within 250 ms (3 overruns kill the app).

## s3w_on_event

```c
void s3w_on_event(const s3w_event_t *e);
```

_api_level 1 · callback the app exports_

One event (see `S3W_EV_*`); e is valid only during the call. Must return within 250 ms (3 overruns kill the app).

## s3w_on_frame

```c
void s3w_on_frame(uint32_t dt_ms);
```

_api_level 1 · callback the app exports_

Canvas mode: called at the requested frame rate ([`s3w_gfx_set_fps`](canvas-mode.md#s3w_gfx_set_fps)) while the app is visible. dt_ms is the time since the previous frame (0 for the first one after start or resume). Must return within 250 ms (3 overruns kill the app).
