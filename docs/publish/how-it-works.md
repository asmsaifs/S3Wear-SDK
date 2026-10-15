# How the store works

**Draft.** This page is a draft that the store team and a lawyer are still reviewing. It is not in force until it is marked final, and it can change.

The store is a **signed index** of apps and watch faces. The Companion app on the phone reads the index, shows the listings
and installs what the user picks on the watch. The watch installs a store package only if the store's key signed it.

## Who builds and signs what

You write and publish the **source**. The store builds it, checks it and signs the result. Neither the check job nor a
submission ever sees the store's signing key:

1. You submit source to a public repository, in the open.
2. Automated checks build and run it in the [dev container](../start/install.md#the-dev-container), with no secrets.
3. A reviewer reads the result and the source.
4. After approval, the store builds the same source again in a trusted job, runs the checks again, and only then signs.

The second build is deliberate: the package people install is always the output of a trusted job from reviewed source, never a
file someone uploaded. This is why the store needs source, and why a binary alone is never accepted.

## What is in the store

- **Apps** (WebAssembly modules) and **watch faces** (data files), free of charge. Paid apps are not part of the store. A listing may
  link to a place to donate.
- Apps that need the Pro firmware say so; the Community edition does not run third-party apps.
- Every listing shows the developer, what the app does, why it needs each permission and each internet host, and where to get
  support and the privacy policy.

## What the store promises

- A first answer to a submission within **7 days**. (This is a target, and the store will say if it changes.)
- Reasons for every refusal, from a fixed list, and one appeal ([updates, takedown and appeals](updates-and-takedown.md)).
- An app's id stays with its first developer ([ids and ownership](ids-and-ownership.md)).

## What the store asks

Follow the [content policy](content-policy.md), the [privacy rules](privacy-rules.md) and the [trademark rules](trademarks.md),
and accept the [developer agreement](developer-agreement.md). The [review guidelines](review-guidelines.md) say what is checked.
