# manifest.json

The manifest is at most 8 KB. Unknown keys are ignored.

```manifest-check
{
  "id": "dev.you.snake",
  "name": "Snake",
  "version": "1.2.0",
  "api_level": 1,
  "category": "game",
  "author": "You",
  "description": "Classic snake with tilt or swipe control.",
  "entry": "app.wasm",
  "ui_mode": "canvas",
  "memory_kb": 384,
  "permissions": ["imu", "audio.play", "storage"],
  "storage_kb": 512,
  "capture_back": false
}
```

## Required

| Key | Rule |
|---|---|
| `id` | Reverse-DNS, at least two parts of `a-z 0-9 _ -`, at most 47 bytes |
| `name` | At most 31 bytes |
| `version` | `MAJOR.MINOR.PATCH` |
| `api_level` | 1 up to the watch's level; the highest level the app uses |
| `ui_mode` | `widgets` or `canvas` |

## Optional

| Key | Meaning |
|---|---|
| `category` | `app` (default), `game`, `tool` or `health`. Faces are separate packages |
| `author`, `description` | Shown in the store and the install screen. The store takes a description of at most 200 characters |
| `entry` | The module's file name in the package; default `app.wasm` |
| `memory_kb` | Linear memory, 64 to 1024; default 256 |
| `permissions` | A list of [permission](../concepts/permissions.md) names; an unknown name is an error |
| `storage_kb` | Storage quota up to 4096; needs `storage` |
| `http_hosts` | Hosts the app may call; needs `phone.http` or `wifi.http` |
| `capture_back` | `true`: the BOOT button is the app's while its screen is up ([input](../guides/input.md)) |
| `tile` | Reserved for [tiles](../guides/tiles.md); ignored today |
| `min_firmware` | `MAJOR.MINOR.PATCH`: the oldest firmware that runs the app |
| `locales` | A list of language tags the app supports |

`s3w build` checks the required keys and the icon before it packs; the watch checks them again when it installs.
