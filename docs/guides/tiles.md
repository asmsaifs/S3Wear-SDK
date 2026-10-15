# Tiles

A tile is a small card an app can show on the watch's tile page (swipe left on the face). Tiles for third-party apps are
**not available yet**: the manifest key `tile` and the export `s3w_tile_render` are reserved, and the watch ignores them.
The watch's own tiles (media, weather, calendar, heart rate) are built in.

Design your app so it is useful without a tile. When tiles open to apps, this page will say how, and apps with
`"tile": true` will be able to render into a card with a once-a-second refresh budget.
