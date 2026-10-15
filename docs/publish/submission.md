# Submission steps

**Draft.** This page is a draft that the store team and a lawyer are still reviewing. It is not in force until it is marked final, and it can change.

Submissions work through pull requests to a public repository, the **store repository**. It opens after the policies are final.
This page describes the flow so you can prepare.

## 1. Prepare the project

An app is an SDK project: `manifest.json`, `src/`, an `icon.png`, optional `assets/` and screenshot scripts (`screens/*.txt`).
A face is a `face.json` and its pictures. Both also need a **`listing.json`** (below). Build and test with
[`s3w run-sim`](../reference/simulator-scripts.md) first, then run the store's own checks on your machine with the same code as
the store's job: [`s3w check`](../reference/cli.md#checking-before-you-submit).

## 2. Add yourself and your id

Add a developer profile (your name, a contact address for the store team, optional website) and the namespaces you own
([ids and ownership](ids-and-ownership.md)). Put the project under `apps/<id>/` or `faces/<id>/`.

## 3. Open a pull request

The checks run on the pull request without secrets and post a report and screenshots on it. Fix what fails: a failed check
cannot be merged. Warnings go to the reviewer.

## 4. Review

A reviewer follows the [review guidelines](review-guidelines.md). The answer is an approval, or a request for changes with one
reason from the list and free text.

## 5. Publish

After the merge the store rebuilds, checks again, signs and publishes; the pull request gets the comment "Published as 1.2.0".
The Companion app shows the listing on its next index refresh.

## listing.json

```json
{
  "developer": "octocat",
  "summary": "One line, 80 characters at most.",
  "support_url": "https://github.com/octocat/watch-snake/issues",
  "source_url": "https://github.com/octocat/watch-snake",
  "privacy_url": "https://example.com/privacy",
  "permission_reasons": { "imu": "Tilt to steer", "audio.play": "Eat and crash sounds" },
  "http_reasons": { "api.example.com": "Weather data" },
  "content_rating": "everyone",
  "screenshot_captions": ["Tilt to steer", "High scores"]
}
```

| Field | Rule |
|---|---|
| `developer` | Your login in the store repository |
| `summary` | One line, at most 80 characters |
| `support_url` | Where users can report problems (an issue tracker, a page, a mail link) |
| `source_url` | Where the source is public |
| `privacy_url` | **Required** if the app uses `phone.http`, `wifi.http`, `location`, `audio.record`, `health.read` or `files` |
| `permission_reasons` | A short, honest reason for **every** permission in the manifest; shown to the user |
| `http_reasons` | A reason for **every** host in `http_hosts` |
| `donate_url` | Optional: a link to donate (https) |
| `content_rating` | `everyone` or `teen` (see the [content policy](content-policy.md)) |
| `screenshot_captions` | At most 8, each at most 60 characters, no more than the screenshots you have |

Reasons are at most 100 characters each. No other fields are allowed: a field the schema does not know is an error.

The exact rules are in the schema (`s3w check --print-schema`); where this page and the schema differ, the schema decides.
