# Preview

Every face package has `preview.png`, 200 × 246 pixels, half the screen. The picker and the phone's store show it. You
do not draw it: `s3w face build` renders it in the simulator with the pinned clock (10:09) and demo data, then reduces it
by averaging.

```bash
s3w face build my-face             # writes my-face/build/preview.png and my-face/build/<id>.s3face
s3w face pack my-face              # packs again with the preview of the last build
s3w face verify my-face/build/<id>.s3face
```

A full-size picture for your own use: `s3w_sim --face my-face --screenshot out.png` (410 × 502).

Look at the preview before you publish. It is what people see when they choose a face, so check that the time reads
clearly and nothing sits in the rounded corners.
