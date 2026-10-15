# Face limits

| Limit | Value |
|---|---|
| `face.json` | 16 KB |
| Elements | 32 (AOD layout: 8) |
| Complication slots | 4; the slot name at most 16 characters |
| `id` | 1 to 47 characters of `a-z 0-9 . _ -`, not starting with `.`, not ending in `.new`, `.old` or `.del` |
| `name` | 32 characters |
| Fixed `text` | 32 characters |
| Image names | 32 characters; 256 KB and 1024 px each |
| Package | 1 MB in all |
| Installed faces | 16 on a watch (24 with the built-in ones) |
| `preview.png` | exactly 200 × 246 |

The package is a zip (stored entries) holding exactly `face.json`, `preview.png`, `signature.sig` and the images
`face.json` names. A stray file is refused. It is signed like an app, with a digest tag of its own so an app signature can
never pass as a face's: by the store key, a trusted developer key, or not at all if the watch allows unsigned packages.
An update must be signed by the same key and not be older.
