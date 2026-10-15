# HTTP through the phone

An app can fetch data over the phone's connection. It needs the `phone.http` [permission](../concepts/permissions.md) (or
`wifi.http`, when the watch has Wi-Fi support) and a list of the hosts it may call in `http_hosts`. A request to any
other host fails with `S3W_ERR_DENIED`.

The call is asynchronous: `s3w_http_request(&req)` returns a request id at once, and `S3W_EV_HTTP` arrives later with
the HTTP status (or a negative `S3W_ERR_*`), in `value`; `x` is the number of body bytes written to your buffer and `y` is
1 if the body was cut at the buffer's size. Keep the response buffer alive until the event.

```c-check
#include "s3w.h"

#define URL "https://api.open-meteo.com/v1/forecast?latitude=47.3&longitude=8.5&current=temperature_2m"

static char s_resp[2048];
static int s_label, s_req;

void s3w_on_start(void)
{
    const int scr = s3w_ui_screen();
    s3w_ui_set_style(scr, S3W_STYLE_PAD, 40);
    s_label = s3w_ui_label(scr, "Loading...", 10);

    s3w_http_req_t req = {0};
    req.method = S3W_HTTP_GET;
    req.url = URL;
    req.url_len = (int)(sizeof(URL) - 1);
    req.resp = s_resp;
    req.resp_cap = sizeof s_resp;
    s_req = s3w_http_request(&req);
    if (s_req < 0) {
        s3w_ui_set_text(s_label, "No phone", 8);
    }
}

void s3w_on_event(const s3w_event_t *e)
{
    if (e->type != S3W_EV_HTTP || e->handle != s_req) {
        return;
    }
    if (e->value == 200) {
        s3w_ui_set_text(s_label, s_resp, e->x < 64 ? e->x : 64); /* a real app parses the JSON */
    } else {
        s3w_ui_set_text(s_label, "Failed", 6);
    }
}
```

With this manifest:

```manifest-check
{
  "id": "dev.you.weather",
  "name": "Weather",
  "version": "0.1.0",
  "api_level": 1,
  "ui_mode": "widgets",
  "memory_kb": 128,
  "permissions": ["phone.http"],
  "http_hosts": ["api.open-meteo.com"]
}
```

## Limits and errors

- URL at most 511 bytes, `http://` or `https://`; request body at most 4 KB (POST); response at most 64 KB; two requests at
  once (`S3W_ERR_NO_RESOURCE` for a third); 20 s timeout (`S3W_ERR_TIMEOUT`).
- `S3W_ERR_NOT_READY`: no phone is connected. Show that to the user and let them retry.
- `S3W_ERR_NETWORK`: the phone could not reach the server.
- Parse small responses in your own code (no libc: write a tiny scanner). Ask the server for only the fields you need.

## Privacy

The request goes through the user's phone to your server. Say in your listing which hosts you call and what you send; the
[store's privacy rules](../publish/index.md) will ask.

In the simulator the script command `app-http <status> [body]` answers the waiting request, so you can test the happy and
error paths without a phone.
