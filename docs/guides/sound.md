# Sound

Sound needs the `audio.play` [permission](../concepts/permissions.md). The volume you pass (0 to 100) scales the
watch's media volume; Silent mode mutes everything.

- **A tone**: `s3w_audio_tone(freq_hz, ms, volume)`, 20 to 8000 Hz for 1 to 10000 ms. A new tone replaces the one playing.
- **A stream**: `s3w_audio_stream_open(16000)` opens a 16 kHz, 16-bit mono PCM stream (only that rate; one at a time).
  `s3w_audio_stream_write(handle, samples, count)` queues samples and returns how many it took; it never waits. The
  buffer holds one second, so feed it a little ahead of the speaker. `s3w_audio_stop(handle)` stops it, or `0` stops
  everything the app plays.
- `s3w_audio_play` (a WAV from the package) returns `S3W_ERR_NOT_FOUND` for now; read a WAV with the files API or embed
  the samples, and feed the stream.

```c-check
#include "s3w.h"

static const int s_notes[] = {523, 659, 784, 1047}; /* C E G C */

void s3w_on_start(void)
{
    const int scr = s3w_ui_screen();
    s3w_ui_set_style(scr, S3W_STYLE_FLEX, S3W_FLEX_COLUMN);
    s3w_ui_set_style(scr, S3W_STYLE_PAD, 40);
    s3w_ui_button(scr, "Play", 4);
}

void s3w_on_event(const s3w_event_t *e)
{
    static int n;
    if (e->type == S3W_EV_CLICK) {
        s3w_audio_tone(s_notes[n++ & 3], 200, 60);
    }
}
```

The manifest needs `"permissions": ["audio.play"]`. Without it the call stops the app.

Keep sounds short. A tone for each button press is fine; a tone that keeps repeating drains the battery and annoys.
