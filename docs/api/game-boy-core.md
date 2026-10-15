# Game Boy core

A native emulator for DMG cartridge files on the card. The app passes the file's path, the buttons and where to draw; the picture is drawn into the canvas by the firmware (canvas apps only). ROMs must be on the card ("/sd/..."), anywhere else is `S3W_ERR_DENIED`. The cartridge RAM is kept next to the ROM as "&lt;name&gt;.sav" (portable to PC emulators). One game at a time.

## s3w_gb_list

```c
int s3w_gb_list(const char *dir, int dl, const char *after, int al, s3w_fs_entry_t *out, int max);
```

_api_level 3 · permission `gameboy`_

Lists a folder of the card for the game library: like [`s3w_fs_list`](device-files.md#s3w_fs_list) (name order, paging by the last name, at most 32 entries per call), but only folders and cartridge files (.gb, .gbc, any case); anything else is left out. The permission "gameboy" is enough: the app cannot see, read or delete other files. `S3W_ERR_DENIED` outside "/sd", `S3W_ERR_NOT_FOUND` (no such folder, or no card).

## s3w_gb_probe

```c
int s3w_gb_probe(const char *path, int len, s3w_gb_info_t *out);
```

_api_level 3 · permission `gameboy`_

Reads the header of a cartridge file into `out`. `S3W_OK`; `S3W_ERR_INVALID`: damaged header, truncated file (`out` is still filled when the header could be read); `S3W_ERR_NOT_FOUND`, `S3W_ERR_DENIED` (not on the card), `S3W_ERR_IO`. Check `out->supported` before loading.

## s3w_gb_load

```c
int s3w_gb_load(const char *path, int len);
```

_api_level 3 · permission `gameboy`_

Opens the cartridge and its save file and resets the console. `S3W_ERR_UNSUPPORTED` (mapper, colour-only game), `S3W_ERR_INVALID` (damaged header, or a save of the wrong size, which is never overwritten), `S3W_ERR_NO_RESOURCE` (a game is already loaded, or out of memory), `S3W_ERR_IO`.

## s3w_gb_unload

```c
int s3w_gb_unload(void);
```

_api_level 3 · permission `gameboy`_

Writes the cartridge RAM if it changed and closes the game (also done when the app ends). `S3W_ERR_NOT_READY`: nothing loaded; `S3W_ERR_IO`: the save could not be written.

## s3w_gb_input

```c
void s3w_gb_input(uint32_t buttons);
```

_api_level 3 · permission `gameboy`_

The buttons held now (`S3W_GB_*` or-ed together); stays until the next call.

## s3w_gb_run_frame

```c
int s3w_gb_run_frame(int x, int y, int scale, uint32_t flags);
```

_api_level 3 · permission `gameboy`_

Runs the console for one video frame (1/59.7 s) and draws it with its top left at (x, y) of the canvas at scale `S3W_GB_SCALE_*`: 160x144, 320x288 or 400x360 px. The whole picture must lie inside the canvas (`S3W_ERR_INVALID`). Only the lines that changed since the last call that drew are written to the canvas and marked as drawn (a still screen costs next to nothing); present as usual ([`s3w_gfx_present`](canvas-mode.md#s3w_gfx_present)). After you draw over the picture (a menu) pass `S3W_GB_REDRAW`; moving it, changing the scale or the palette redraws it by itself. `S3W_GB_NO_DRAW` emulates the frame without drawing: when the display cannot keep up, run the missed frames this way and draw only the last, so the game keeps its speed (the app paces: dt_ms of [`s3w_on_frame`](lifecycle.md#s3w_on_frame) / 16.74 ms per frame). Returns the milliseconds it took, `S3W_ERR_NOT_READY` (nothing loaded, or drawing without a canvas), `S3W_ERR_IO` (the card failed mid-game: stop), `S3W_ERR_UNSUPPORTED` (the game did something the core cannot do).

## s3w_gb_flush_ram

```c
int s3w_gb_flush_ram(void);
```

_api_level 3 · permission `gameboy`_

Writes the cartridge RAM now if it changed.

## s3w_gb_set_palette

```c
int s3w_gb_set_palette(const uint16_t *pal);
```

_api_level 3 · permission `gameboy`_

The four shades from lightest to darkest, RGB565 (default: white to black).

## s3w_gb_save_state

```c
int s3w_gb_save_state(int slot);
```

_api_level 3 · permission `gameboy`_

Save states: the whole console in "&lt;game&gt;.st&lt;slot&gt;" next to the ROM (slot 0..3; the card, not the flash). [`s3w_gb_save_state`](#s3w_gb_save_state) writes it atomically; [`s3w_gb_load_state`](#s3w_gb_load_state) puts the console back (the next frame is drawn in full). Errors: `S3W_ERR_NOT_READY` (nothing loaded), `S3W_ERR_INVALID` (slot, or a file that is not a state of this game and this firmware's core, or damaged: the console is left as it was), `S3W_ERR_NOT_FOUND` (load: no such state), `S3W_ERR_IO`. A state does not survive a firmware update that changes the core.

## s3w_gb_load_state

```c
int s3w_gb_load_state(int slot);
```

_api_level 3 · permission `gameboy`_

Puts the console back to the state saved in slot by [`s3w_gb_save_state`](#s3w_gb_save_state); errors as there.

## s3w_gb_set_audio

```c
int s3w_gb_set_audio(bool on, int volume);
```

_api_level 3 · permission `gameboy` and `audio.play`_

The console's sound: on = true opens the 16 kHz PCM stream (the one [`s3w_audio_stream_open`](audio.md#s3w_audio_stream_open) uses: one at a time, `S3W_ERR_NO_RESOURCE` while the app has its own open) and from then on every frame run by [`s3w_gb_run_frame`](#s3w_gb_run_frame), drawn or not, adds its sound (mono, volume 0..100 of full); false closes it. Calling again with on = true only changes the volume. Needs "audio.play" as well as "gameboy". Sound that is more than about 150 ms ahead of the speaker is dropped, so the picture can fall behind without the sound lagging. Muted by the watch's Silent mode like any stream. `S3W_ERR_UNSUPPORTED`: no audio on this watch. The sound registers follow the game whether or not sound is on, and switching it on mid-game plays what is playing.
