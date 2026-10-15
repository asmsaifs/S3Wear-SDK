# API reference

The app API of the S3Wear watch, api_level 3. Generated from `include/s3w.h`; every function has the api_level that added it, and the permission it needs, if any. A manifest's `api_level` must not be higher than the watch's.

| Page | Functions |
|---|---|
| [Lifecycle](lifecycle.md) | 6 |
| [System](system.md) | 9 |
| [Widgets mode](widgets-mode.md) | 18 |
| [Canvas mode](canvas-mode.md) | 12 |
| [Sensors](sensors.md) | 3 |
| [Audio](audio.md) | 7 |
| [Storage](storage.md) | 8 |
| [Device files](device-files.md) | 5 |
| [Game Boy core](game-boy-core.md) | 11 |
| [Health](health.md) | 1 |
| [Network](network.md) | 1 |
| [Notifications](notifications.md) | 1 |
| [Game services](game-services.md) | 3 |
| [Constants and types](constants.md) | |
| [Watch face registry](faces.md) | |

## Permissions

A function that needs a permission traps the app when the manifest lacks it.

| Permission | Functions |
|---|---|
| `audio.play` | [`s3w_audio_tone`](audio.md#s3w_audio_tone), [`s3w_audio_play`](audio.md#s3w_audio_play), [`s3w_audio_stream_open`](audio.md#s3w_audio_stream_open), [`s3w_audio_stream_write`](audio.md#s3w_audio_stream_write), [`s3w_audio_stop`](audio.md#s3w_audio_stop), [`s3w_gb_set_audio`](game-boy-core.md#s3w_gb_set_audio) |
| `audio.record` | [`s3w_mic_start`](audio.md#s3w_mic_start), [`s3w_mic_stop`](audio.md#s3w_mic_stop) |
| `files` | [`s3w_ui_image_file`](widgets-mode.md#s3w_ui_image_file), [`s3w_fs_list`](device-files.md#s3w_fs_list), [`s3w_fs_delete`](device-files.md#s3w_fs_delete), [`s3w_fs_open`](device-files.md#s3w_fs_open), [`s3w_fs_read`](device-files.md#s3w_fs_read), [`s3w_fs_close`](device-files.md#s3w_fs_close) |
| `gameboy` | [`s3w_gb_list`](game-boy-core.md#s3w_gb_list), [`s3w_gb_probe`](game-boy-core.md#s3w_gb_probe), [`s3w_gb_load`](game-boy-core.md#s3w_gb_load), [`s3w_gb_unload`](game-boy-core.md#s3w_gb_unload), [`s3w_gb_input`](game-boy-core.md#s3w_gb_input), [`s3w_gb_run_frame`](game-boy-core.md#s3w_gb_run_frame), [`s3w_gb_flush_ram`](game-boy-core.md#s3w_gb_flush_ram), [`s3w_gb_set_palette`](game-boy-core.md#s3w_gb_set_palette), [`s3w_gb_save_state`](game-boy-core.md#s3w_gb_save_state), [`s3w_gb_load_state`](game-boy-core.md#s3w_gb_load_state), [`s3w_gb_set_audio`](game-boy-core.md#s3w_gb_set_audio) |
| `health.read` | [`s3w_health_today`](health.md#s3w_health_today) |
| `imu` | [`s3w_imu_start`](sensors.md#s3w_imu_start), [`s3w_imu_stop`](sensors.md#s3w_imu_stop), [`s3w_tilt`](sensors.md#s3w_tilt) |
| `keep_screen_on` | [`s3w_keep_screen_on`](system.md#s3w_keep_screen_on) |
| `notify` | [`s3w_notify`](notifications.md#s3w_notify) |
| `phone.http` | [`s3w_http_request`](network.md#s3w_http_request) |
| `wifi.http` | [`s3w_http_request`](network.md#s3w_http_request) |

## By api_level

| api_level | New functions |
|---|---|
| 1 | 68 functions: the original API |
| 2 | `s3w_ui_image_file`, `s3w_fs_list`, `s3w_fs_delete`, `s3w_fs_open`, `s3w_fs_read`, `s3w_fs_close` |
| 3 | `s3w_gb_list`, `s3w_gb_probe`, `s3w_gb_load`, `s3w_gb_unload`, `s3w_gb_input`, `s3w_gb_run_frame`, `s3w_gb_flush_ram`, `s3w_gb_set_palette`, `s3w_gb_save_state`, `s3w_gb_load_state`, `s3w_gb_set_audio` |
