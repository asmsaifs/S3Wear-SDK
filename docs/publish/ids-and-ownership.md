# Ids and ownership

**Draft.** This page is a draft that the store team and a lawyer are still reviewing. It is not in force until it is marked final, and it can change.

An app or face **id** is its permanent name (`io.github.octocat.snake`). The watch uses it to find the app's files and to decide
whether an update may replace an installed copy. The store keeps ids from clashing:

- **A GitHub login** owns `io.github.<login>.*` from its first submission.
- **A domain** (`com.example.*`) needs proof: a DNS TXT record `s3wear-developer=<login>` on that domain, which the checks
  verify when your profile lists it.
- **Reserved**: `dev.s3wear.*`, `s3w.*`, `com.s3wear.*`, and the ids of the built-in faces. Nobody else may use them.
- **An id belongs to its first developer for good.** It can move only through the store team, on request from both sides.
- A change to an app's folder from anyone but its owner is refused by the checks.

Why so strict: the watch also refuses an update signed by a different key than the installed copy, so an id is the identity of the
app and of its users' data. Taking over an id would take over both.

## Choosing an id

Use one you will keep: renaming means publishing a new app, and users of the old one do not move over. Lower case letters,
digits, `_` and `-` in at least two dot-separated parts, at most 47 bytes in all.
