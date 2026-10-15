# Device files

The watch's own files, not the app's: the internal flash "/flash" and the card "/sd" (only while one is in). Paths are absolute, '/'-separated, without "." or ".." parts, at most `S3W_FS_PATH_MAX` bytes. "/" lists the roots. All of the card is open; of the flash only the user's data: /flash/memos, /flash/shots and /flash/logs (everything else there is the system's: apps, keys, settings, stores). Other paths in /flash are not listed and give `S3W_ERR_DENIED`. Names that start with '.' (temporary files) are not listed, and neither is an entry whose name is longer than `S3W_FS_NAME_MAX` bytes.

## s3w_fs_list

```c
int s3w_fs_list(const char *dir, int dl, const char *after, int al, s3w_fs_entry_t *out, int max);
```

_api_level 2 · permission `files`_

Lists a directory in name order (ASCII letters ignore their case; directories and files together): the entries whose name sorts after `after` (al = 0: from the first), at most max of them. Paging: pass the last name of a page to get the next, so the pages stay right while files come and go. Returns how many were written (0 = past the end), `S3W_ERR_NOT_FOUND` (no such directory, or no card), `S3W_ERR_DENIED`, `S3W_ERR_INVALID` (path, `after` longer than `S3W_FS_NAME_MAX`, max 1..32).

## s3w_fs_delete

```c
int s3w_fs_delete(const char *path, int len);
```

_api_level 2 · permission `files`_

Deletes a file or an empty directory (one that holds only hidden files, which are not listed, counts as empty and they go with it). `S3W_ERR_NOT_FOUND`, `S3W_ERR_DENIED` (not a user place, a root, or a directory with anything else in it), `S3W_ERR_IO`.

## s3w_fs_open

```c
int s3w_fs_open(const char *path, int len);
```

_api_level 2 · permission `files`_

Opens a file for reading; one at a time (`S3W_ERR_NO_RESOURCE` while another is open). Returns the file's size in bytes (a file over 2 GB: `S3W_ERR_INVALID`) or `S3W_ERR_NOT_FOUND` / `S3W_ERR_DENIED`. Closed with the app.

## s3w_fs_read

```c
int s3w_fs_read(void *buf, int n);
```

_api_level 2 · permission `files`_

Bytes read from the open file (0 at the end), up to n (≤ 4096 per call). `S3W_ERR_NOT_READY`: none is open.

## s3w_fs_close

```c
void s3w_fs_close(void);
```

_api_level 2 · permission `files`_

Closes the file opened by [`s3w_fs_open`](#s3w_fs_open) (also done when the app ends).
