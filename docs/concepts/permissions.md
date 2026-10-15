# Permissions and consent

An app can use the screen, touch, time, timers and its own storage (256 KB) with no permission. Anything that touches
more needs a permission named in the manifest:

```manifest-check
{
  "id": "dev.you.weather",
  "name": "Weather",
  "version": "0.1.0",
  "api_level": 1,
  "ui_mode": "widgets",
  "memory_kb": 128,
  "permissions": ["phone.http", "storage"],
  "http_hosts": ["api.open-meteo.com"],
  "storage_kb": 512
}
```

| Permission | Grants | Asked |
|---|---|---|
| `storage` | App storage up to `storage_kb` (≤ 4096) instead of 256 KB | No |
| `imu` | Accelerometer stream and tilt | At install |
| `audio.play` | Tones and sound | At install |
| `audio.record` | The microphone (not available yet) | Each session |
| `health.read` | Steps, sleep and activity summaries (not available yet) | At install |
| `notify` | Post a notification | At install |
| `phone.http`, `wifi.http` | HTTP through the phone or Wi-Fi, only to `http_hosts` | At install |
| `location` | Coarse location from the phone (not available yet) | Each session |
| `keep_screen_on` | Hold the screen on while the app is in front | No |
| `files` | Browse and delete the user's files, show pictures from them (api_level 2) | At install |
| `gameboy` | Run Game Boy cartridge files from the card (api_level 3, Pro) | At install |

Every call is checked: a function that needs a permission your manifest lacks **stops the app** with
`name: needs permission x`. Each function in [the reference](../api/index.md#permissions) lists the permission it needs.

## The consent screen

When someone installs your app, the watch (and the phone) shows what it asks for in plain words and the user taps
Install or cancels. Ask for what the app needs and no more: a long list makes people say no, and the store's review
checks that each permission is used.

## HTTP hosts

`http_hosts` is an allowlist of host names. A request to any other host fails with `S3W_ERR_DENIED`. List only the
hosts you call; see [HTTP through the phone](../guides/http.md).
