# Updates, takedown and appeals

**Draft.** This page is a draft that the store team and a lawyer are still reviewing. It is not in force until it is marked final, and it can change.

## Updates

An update is a new pull request with a higher version number. It goes through the same automated checks and a review of the
difference to the last approved version. Users see updates in the Companion app.

An update must keep the id, and the watch only accepts it if it is signed by the same key as the installed copy: the store signs
every store package with one key, so store updates always line up. Someone who installed your app by hand with a developer
key has to uninstall that copy first.

Do not make an update that changes what the app does or collects without saying so in the listing and the privacy policy.

## Takedown

The store can remove an app, a version of it, or a developer's apps when:

- it breaks the [content policy](content-policy.md), the [privacy rules](privacy-rules.md) or the [trademark rules](trademarks.md);
- it is harmful to the watch or to people, or behaves differently from what was reviewed;
- a rights owner or a court asks for it and the request holds up; or
- the developer asks for it.

Removal has two parts. The listing leaves the store. And the store adds the id and versions to a **revoked list** inside the
signed index: the Companion app reads it, tells people who have the app installed, and offers to uninstall it. For something
dangerous, a later firmware can refuse to start a revoked app until it is uninstalled.

The developer gets the **reason** by message, and the same fixed list as for reviews applies.

## Appeals

You can **reply once** to a refusal or a takedown with new information. A different member of the store team looks at it and
answers, normally within 14 days. The answer is final for that version. A fixed version can always be submitted again.

## Reports from users

The details page of every app has a **Report** button that opens a message to the store team. Reports about safety, privacy and
rights are handled first. Real issues go to you: you will find them at your `support_url`.
