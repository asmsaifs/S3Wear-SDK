# Storage

The app's own files: `S3W_STORAGE_DEFAULT_KB` in all, or the manifest's quota with the "storage" permission (no permission needed). Keys and file names: 1..`S3W_NAME_MAX` bytes of [A-Za-z0-9._-], not starting with '.' (`S3W_ERR_INVALID` otherwise).

## s3w_kv_get

```c
int s3w_kv_get(const char *k, int kl, void *buf, int cap);
```

_api_level 1_

The value's length (copies at most cap bytes), or `S3W_ERR_NOT_FOUND`.

## s3w_kv_set

```c
int s3w_kv_set(const char *k, int kl, const void *v, int vl);
```

_api_level 1_

vl ≤ `S3W_KV_VALUE_MAX`. `S3W_ERR_NO_SPACE` over the quota.

## s3w_kv_delete

```c
int s3w_kv_delete(const char *k, int kl);
```

_api_level 1_

Deletes a key. `S3W_OK`, or a negative `S3W_ERR_*` (`S3W_ERR_INVALID` for a bad key).

## s3w_file_open

```c
int s3w_file_open(const char *name, int len, int mode);
```

_api_level 1_

mode `S3W_FILE_*`: returns fd (≥ 1), `S3W_ERR_NOT_FOUND` (read), `S3W_ERR_NO_RESOURCE` (4 open).

## s3w_file_read

```c
int s3w_file_read(int fd, void *buf, int n);
```

_api_level 1_

Bytes read (0 at the end) or written (`S3W_ERR_NO_SPACE` over the quota).

## s3w_file_write

```c
int s3w_file_write(int fd, const void *buf, int n);
```

_api_level 1_

Writes n bytes to a file opened with `S3W_FILE_WRITE` or `S3W_FILE_APPEND`. Returns the bytes written, or `S3W_ERR_NO_SPACE` over the quota.

## s3w_file_close

```c
void s3w_file_close(int fd);
```

_api_level 1_

Closes a file.

## s3w_file_delete

```c
int s3w_file_delete(const char *name, int len);
```

_api_level 1_

Deletes one of the app's files. `S3W_OK`, or a negative `S3W_ERR_*` (`S3W_ERR_NOT_FOUND` if there is none).
