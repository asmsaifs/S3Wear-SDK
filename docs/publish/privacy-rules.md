# Privacy rules

**Draft.** This page is a draft that the store team and a lawyer are still reviewing. It is not in force until it is marked final, and it can change.

People wear the watch all day. These rules protect what it knows about them.

## What an app can touch

An app has no access to the user's data unless the manifest asks for a [permission](../concepts/permissions.md) and the user agrees
at install. The data an app may reach, and may therefore have to explain:

| Permission | The app can reach |
|---|---|
| `phone.http`, `wifi.http` | The internet, to the hosts you list. **Anything the app sends there leaves the watch** |
| `health.read` | Steps, sleep, activity |
| `location` | Coarse location from the phone |
| `audio.record` | The microphone |
| `files` | The user's files on the watch: the card, memos, screenshots, logs |

## The rules

1. **Say what you collect.** If the app uses one of the permissions above, the listing needs a **privacy policy** (`privacy_url`),
   in plain language: what the app sends or keeps, why, where it goes, how long it stays, and how to ask for deletion.
2. **Send only what the feature needs**, and only to the hosts you list with a reason. No unrelated data "while we are there".
3. **No sale and no sharing for advertising.** Data from an app is not sold, rented or used to build profiles of people.
4. **No tracking.** Do not build or send identifiers meant to follow a person or watch across apps, sessions or services.
   An id you need to make a feature work (a game's player name the user chose) is fine if the policy says so.
5. **Sensitive data stays on the watch** unless the user does something that clearly sends it. Health, location, voice and file
   content do not go to a server because the app can.
6. **No hidden behaviour.** What the policy says is what the app does. A change in what you collect needs a new version and an
   updated policy.
7. **Keep it safe.** Use `https://` for anything personal. Do not put secrets in the app: it is public source.
8. **Delete on request.** If you keep data about someone on a server, you delete it when they ask, and the policy says how to ask.

## What the reviewer checks

The reviewer compares the app with the listing: each permission has a reason that fits a feature; each host has a reason; the
privacy policy exists, can be opened, covers the data the app handles, and does not contradict the code. An app that sends data
the policy does not mention is refused (`policy-privacy`) or, if it is found later, removed.

## Apps that collect nothing

If the app uses none of the permissions in the table, it needs no privacy policy. Say so in the description ("collects nothing") if
you like: it is a reason to install it.
