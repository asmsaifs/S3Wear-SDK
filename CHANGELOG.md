# Changelog

New natives and permissions per api_level.

## SDK 0.2.0
No new natives (api_level stays 3). New in the tools:
- `s3w check`: the store's automated checks on your machine (layout, `listing.json`, manifest, ownership, build, version,
  api_level, icon, screenshots, headless run, a 2-minute monkey test, callback times, permissions, content policy).
- Watch faces with pictures: `s3w new --face`, `s3w face run-sim` (reload and a demo-data switcher), `s3w face build`
  checks every PNG. Needs firmware 0.2.3 or newer to show the pictures.
- The dev container image carries `dig` for the DNS ownership check and the simulator 0.2.3.

## api_level 1
First public release.
