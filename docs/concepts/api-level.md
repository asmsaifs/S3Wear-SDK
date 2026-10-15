# api_level and compatibility

`api_level` is the version of the app API. `s3w.h` defines `S3W_API_LEVEL` (currently 3), and every function in the
[reference](../api/index.md#by-api_level) says the level that added it.

| api_level | Added |
|---|---|
| 1 | The original API: lifecycle, widgets, canvas, input, sensors, audio, storage, network, notifications, game services |
| 2 | Device files (`s3w_fs_*`, `s3w_ui_image_file`) |
| 3 | The Game Boy core (`s3w_gb_*`) |

The manifest's `api_level` is the **highest** level your app uses. A watch with older firmware refuses an app whose
level it does not have, and shows why. Set the lowest level that has what you call, so the app runs on the most
watches.

## The promise

A function is never removed or changed in a way that breaks an app. An app built for api_level 1 keeps working on every
later firmware. New functions and permissions come with a new level, listed in the SDK's changelog. The store rebuilds
and re-checks every app against each new simulator before a firmware release.

`s3w run-sim` warns when your manifest asks for more than the simulator runs. Declare the level of the newest function
you call: the manifest is what the watch checks, not your code.

## min_firmware

The manifest may also carry `min_firmware` (a `MAJOR.MINOR.PATCH`). Use it for a fix you depend on that is not an API
change.
