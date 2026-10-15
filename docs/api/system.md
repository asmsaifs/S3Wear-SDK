# System

## s3w_millis

```c
uint32_t s3w_millis(void);
```

_api_level 1_

Milliseconds since the app started (monotonic).

## s3w_time_unix

```c
int64_t s3w_time_unix(void);
```

_api_level 1_

Seconds since 1970 (UTC), or 0 while the watch does not know the time.

## s3w_time_local

```c
int s3w_time_local(s3w_tm_t *out);
```

_api_level 1_

Local time in the watch's time zone. `S3W_ERR_NOT_READY` while the time is unknown.

## s3w_log

```c
void s3w_log(int level, const char *msg, int len);
```

_api_level 1_

Writes msg (UTF-8, len bytes) to the app log at a level `S3W_LOG_*`; `s3w logs` shows it.

## s3w_exit

```c
void s3w_exit(void);
```

_api_level 1_

Ends the app at once ([`s3w_on_stop`](lifecycle.md#s3w_on_stop) is not called).

## s3w_timer_start

```c
int s3w_timer_start(uint32_t period_ms, bool repeat);
```

_api_level 1_

Starts a timer (at least 20 ms, up to 8 at once): `S3W_EV_TIMER` with its id after each period. Returns the id (&gt; 0) or `S3W_ERR_*`.

## s3w_timer_stop

```c
void s3w_timer_stop(int id);
```

_api_level 1_

Stops a timer. An id that is not running (a one-shot that fired) is ignored.

## s3w_keep_screen_on

```c
void s3w_keep_screen_on(bool on);
```

_api_level 1 · permission `keep_screen_on`_

Holds the screen on while the app is in the foreground (released when it ends).

## s3w_locale

```c
int s3w_locale(char *buf, int cap);
```

_api_level 1_

The UI language as a BCP 47 tag ("en", "de", "bn"), like snprintf: writes at most cap bytes including a terminating NUL and returns the tag's length.
