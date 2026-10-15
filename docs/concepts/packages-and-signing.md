# Packages and signing

`s3w build` makes `build/<id>.s3app`: a zip (entries stored, not compressed) with

```
manifest.json
app.wasm
icon.png          optional, 80 x 80
assets/...        optional
signature.sig     the signer's public key and an Ed25519 signature
```

Rules the watch checks on install: at most 64 entries and 4 MB; names of at most 63 bytes of `A-Za-z0-9._-` in
`/`-separated parts; every CRC correct; `data/` is reserved for the app's storage; the module loads; the icon decodes.
`s3w verify <pkg>` checks the same things on your PC.

## Who signed it

The signature must come from a key the watch trusts:

- **The store key**: apps installed from the store.
- **A trusted developer key**: yours, once you add it. `s3w keygen` makes `~/.s3w/dev.key`; the first
  `s3w install --usb --trust-key` adds its public half to the watch (`app key add <hex>` on the console does the same).
- **No signature**: only with the watch's developer option "unsigned apps" (`settings set dev_unsigned 1`).

An update must be signed by the same key as the installed version, and must not be older. This stops another package
taking over your app id and its data. To switch keys, uninstall first.

## The id

`id` is reverse-DNS (`dev.you.counter`): at least two parts of `a-z 0-9 _ -`, at most 47 bytes. The ids of the watch's
preinstalled apps are taken. In the store, ids are tied to your developer account ([publish](../publish/index.md)).

## Icons

`icon.png` is shown in the launcher: 80 × 80, 8-bit (grey, RGB, palette, grey + alpha or RGBA), not interlaced, at most
64 KB, round with transparent corners. `s3w build` checks it. Without one the launcher shows the first letter of the
name.
