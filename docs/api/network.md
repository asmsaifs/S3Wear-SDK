# Network

`S3W_HTTP_GET` / `S3W_HTTP_POST`

http:// or https://, ≤ `S3W_HTTP_URL_MAX` bytes; its host must be

in the manifest's allowlist (`S3W_ERR_DENIED` otherwise)

POST

POST, ≤ `S3W_HTTP_BODY_MAX` bytes

the response body goes here: keep it until `S3W_EV_HTTP`

0..`S3W_HTTP_RESP_MAX`

36 bytes

## s3w_http_request

```c
int s3w_http_request(const s3w_http_req_t *req);
```

_api_level 1 · permission `phone.http` or `wifi.http`_

Through the phone (Wi-Fi comes later). Returns the request id (`S3W_EV_HTTP` follows), `S3W_ERR_NOT_READY` (no phone), `S3W_ERR_NO_RESOURCE` (`S3W_HTTP_MAX` running).
