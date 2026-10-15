# Storage

Each app has private storage that other apps cannot read. It survives restarts, reboots and updates, and is removed
when the app is uninstalled (after the user confirms).

| | |
|---|---|
| Quota | 256 KB without a permission; with `storage`, the manifest's `storage_kb` (up to 4096) |
| Key-value | `s3w_kv_get`, `s3w_kv_set`, `s3w_kv_delete`: values up to 4 KB, written atomically |
| Files | `s3w_file_open`, `read`, `write`, `close`, `delete`: flat names, at most 4 open |
| Names | 1 to 32 bytes of `A-Z a-z 0-9 . _ -`, not starting with `.` (anything else is `S3W_ERR_INVALID`) |
| Full | `S3W_ERR_NO_SPACE` |
| High scores | Kept separately, not counted in the quota |

```c-check
#include "s3w.h"

typedef struct {
    int level;
    int coins;
} save_t;

static save_t s_save;

static void load(void)
{
    save_t tmp;
    if (s3w_kv_get("save", 4, &tmp, sizeof tmp) == (int)sizeof tmp) {
        s_save = tmp;
    }
}

static void store(void)
{
    if (s3w_kv_set("save", 4, &s_save, sizeof s_save) == S3W_ERR_NO_SPACE) {
        s3w_ui_toast("Storage full", 12);
    }
}

void s3w_on_start(void)
{
    load();
    s_save.level++;
    store();
}
```

Save on every change that matters. The watch can end the app between callbacks; `s3w_on_stop` is not called in every
case. Keep saved formats versioned (a leading version number) so a later update of the app can read old saves.

The user's own files (the SD card, memos) are a different API, [device files](../api/device-files.md), behind the
`files` permission.
