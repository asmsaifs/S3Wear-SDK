# Health

## s3w_health_today

```c
int s3w_health_today(s3w_health_summary_t *out);
```

_api_level 1 · permission `health.read`_

Today's totals. `S3W_ERR_UNSUPPORTED` until the watch has activity tracking.
