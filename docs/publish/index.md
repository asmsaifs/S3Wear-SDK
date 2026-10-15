# Publish

How an app or watch face gets into the S3Wear store, what the store expects of you, and what you can expect of the store.

**Status:** submissions from outside developers are **not open yet**. The pages in this section are the rules the store will
work by; the policy pages are drafts that are still being reviewed.

| Page | What it covers |
|---|---|
| [How the store works](how-it-works.md) | What the store is, who builds and signs what, and why |
| [Submission steps](submission.md) | From a project to a published listing, and the `listing.json` file |
| [Ids and ownership](ids-and-ownership.md) | Who may use which app id |
| [Review guidelines](review-guidelines.md) | What the automated checks and the reviewer look for |
| [Content policy](content-policy.md) | What may and may not be in an app, a face or a listing |
| [Privacy rules](privacy-rules.md) | What may leave the watch, and what you must tell people |
| [Trademarks](trademarks.md) | Using the S3Wear name, and other people's names |
| [Updates, takedown and appeals](updates-and-takedown.md) | New versions, removing an app, and disagreeing with a decision |
| [Developer agreement](developer-agreement.md) | The terms between you and the store |

## What you can do today

- **Share an app or a face as a file.** `s3w build` makes a signed `.s3app`; `s3w face build` a `.s3face`. Anyone with a
  Pro watch can install a package that is signed by a key they trust, or any package when they turn on the
  "unsigned apps" developer option. Keep your key safe: it is the identity of your apps (an update must use the same one).
- **Use the store as a user.** The Companion app browses the store's apps and faces and installs them on the watch.

## Make your app ready

Things that will matter, and cost nothing to do now:

- Ask for the fewest [permissions](../concepts/permissions.md) the app needs, and use each one.
- List only the hosts you call in `http_hosts`, and say in the description what the app sends.
- Give it an [icon](../guides/icons-and-screenshots.md) and a screenshot script.
- Test it with a [simulator script](../guides/testing.md) that runs it for a few hundred frames without a trap.
- Keep the app small, and do not use trademarks or other people's content you have no right to.
