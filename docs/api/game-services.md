# Game services

## s3w_highscore_submit

```c
int s3w_highscore_submit(int board, int score);
```

_api_level 1_

Records score on board (0..`S3W_HIGHSCORE_BOARDS` - 1) if it beats the best: higher wins, or lower with `S3W_HIGHSCORE_LOWER` (times). Kept in the app's storage (not counted in its quota), so it survives restarts and updates. Returns 1 for a new best, 0 if not, or `S3W_ERR_*`.

## s3w_highscore_get

```c
int s3w_highscore_get(int board, int *best);
```

_api_level 1_

The board's best: `S3W_OK` with \*best, or `S3W_ERR_NOT_FOUND` before the first score.

## s3w_random

```c
int s3w_random(void);
```

_api_level 1_

A random number 0..0x7FFFFFFF (the watch's hardware RNG).
