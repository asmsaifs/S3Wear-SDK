# Notifications

## s3w_notify

```c
int s3w_notify(const char *title, int tl, const char *body, int bl);
```

_api_level 1 · permission `notify`_

A notification from the app (at most one every 10 s: `S3W_ERR_NO_RESOURCE`).
