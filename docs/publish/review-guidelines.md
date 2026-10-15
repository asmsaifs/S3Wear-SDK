# Review guidelines

**Draft.** This page is a draft that the store team and a lawyer are still reviewing. It is not in force until it is marked final, and it can change.

Every submission goes through automated checks and then a person. These guidelines say what both look for, so you can check
your app before you submit it.

## Automated checks

They must pass before a reviewer sees the submission.

| Check | Fails when |
|---|---|
| Layout | Files outside the allowed set; `listing.json` missing or invalid |
| Manifest, `face.json` | Any rule of [the manifest](../reference/manifest.md) or [the face format](../reference/face-json.md) |
| Ownership | An id outside your namespaces; changes to another developer's files |
| Build | The build fails; the module imports anything but the S3Wear API; the package is over 4 MB (faces 1 MB) |
| Version | Not higher than the published version |
| api_level | Above the newest released firmware |
| Icon, screenshots | The [icon rules](../guides/icons-and-screenshots.md); screenshot scripts that fail |
| Run | The app traps in its first 12 seconds, or in a two-minute test of random taps, swipes, drags, tilting and (for an app that captures BOOT) BOOT presses: no trap, no watchdog kill, no UI handles or timers that only ever grow. The test is repeatable: the report names the seed, and `s3w check --seed` plays the same run |
| Budget | A callback over the 250 ms limit. Over 50 ms at the 99th percentile is a warning: the watch is slower than the simulator |
| Permissions | A permission or host without a reason; a listed permission the code never uses (a warning) |
| Content | The [content policy](content-policy.md) rules that a program can check, and a list of names and words |
| Sizes | Names, summaries and captions over their limits |

## What the reviewer checks

- **It does what the listing says**, and nothing is hidden behind a timer, a date or a server switch.
- **Permissions match the features**; each internet host matches its reason; the privacy policy exists and fits what the app
  does ([privacy rules](privacy-rules.md)).
- **It is smooth**: a canvas game holds at least 25 frames a second on the main screen of a real Pro watch. The reviewer installs it
  with `s3w install --usb` and plays it.
- **It is readable** at 410 × 502 and with the system's large text setting, and keeps clear of the rounded corners.
- **The content is allowed** ([content policy](content-policy.md)).
- **For an update**, the reviewer reads the difference to the last approved version.

## The answer

A pull request review, with one reason from this list and free text:

| Reason | Meaning |
|---|---|
| `policy-content` | The content policy is not met |
| `policy-privacy` | The privacy rules are not met, or the privacy policy is missing or wrong |
| `broken` | It crashes, hangs, or does not do what it says |
| `misleading-listing` | The listing promises what the app does not do, or hides what it does |
| `performance` | Too slow on a real watch |
| `other` | Something else, explained in the text |

The first answer comes within 7 days. You can fix the points and push again; the review continues on the same pull request.
