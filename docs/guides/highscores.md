# High scores

The watch keeps up to eight best values per app, one for each **board** (0 to 7), in the app's storage. They are not
counted in your quota and survive restarts, reboots and updates.

- `s3w_highscore_submit(board, score)` records `score` if it beats the best and returns 1 for a new best, 0 if not.
  Higher wins. For times (lower is better) or the board with `S3W_HIGHSCORE_LOWER`: `board | S3W_HIGHSCORE_LOWER`.
- `s3w_highscore_get(board, &best)` gives `S3W_OK` and the best, or `S3W_ERR_NOT_FOUND` before the first score.
- `s3w_random()` is a number from 0 to 0x7FFFFFFF from the watch's hardware generator (the simulator uses a generator
  driven by the app's clock, so scripted runs repeat).

```c-check
#include "s3w.h"

void game_over(int score_points, int time_ms)
{
    if (s3w_highscore_submit(0, score_points) == 1) {
        s3w_ui_toast("New best!", 9);
    }
    s3w_highscore_submit(1 | S3W_HIGHSCORE_LOWER, time_ms); /* board 1: fastest time */
}

int best_score(void)
{
    int best = 0;
    return s3w_highscore_get(0, &best) == S3W_OK ? best : 0;
}
```

Scores are local to the watch. Do not rely on them as proof of anything.
