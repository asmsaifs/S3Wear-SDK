# Audio

volume is 0..100 of the watch's media volume in every audio function; Silent mutes.

## s3w_audio_tone

```c
int s3w_audio_tone(int freq_hz, int ms, int volume);
```

_api_level 1 · permission `audio.play`_

A tone, freq_hz 20..8000 for ms 1..10000 (replaces the app's tone if one plays).

## s3w_audio_play

```c
int s3w_audio_play(const char *asset, int len, int volume);
```

_api_level 1 · permission `audio.play`_

A WAV from the app's assets. `S3W_ERR_NOT_FOUND` for now: packages carry assets/, but loading them is not done yet.

## s3w_audio_stream_open

```c
int s3w_audio_stream_open(int sample_rate);
```

_api_level 1 · permission `audio.play`_

16-bit mono PCM; sample_rate 16000 only (else `S3W_ERR_UNSUPPORTED`). One stream: returns its handle. The volume is the media volume.

## s3w_audio_stream_write

```c
int s3w_audio_stream_write(int h, const int16_t *pcm, int samples);
```

_api_level 1 · permission `audio.play`_

Queues samples without waiting (the buffer holds 1 s); returns how many were taken.

## s3w_audio_stop

```c
void s3w_audio_stop(int h);
```

_api_level 1 · permission `audio.play`_

Stops a stream (its handle), or with 0 the app's tone and stream.

## s3w_mic_start

```c
int s3w_mic_start(int sample_rate);
```

_api_level 1 · permission `audio.record`_

Starts the microphone. `S3W_ERR_UNSUPPORTED` until the watch has voice support.

## s3w_mic_stop

```c
void s3w_mic_stop(void);
```

_api_level 1 · permission `audio.record`_

Stops the microphone.
