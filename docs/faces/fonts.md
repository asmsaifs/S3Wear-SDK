# Fonts

A `text` element's `font` is one of these (the name carries the size in pixels):

| Name | Use |
|---|---|
| `digits_160` | The biggest time |
| `digits_96` | Large time |
| `digits_96_light` | The same in a light weight, for the always-on layout |
| `title_32` | Headings, secondary numbers |
| `body_26` | The default: dates, labels |
| `caption_22` | Small captions |

The list is generated from the watch ([face registry](../api/faces.md#fonts)); an unknown font name is an error.
The three `digits_*` fonts draw only digits and `: . , - + %`: use `body_26` or `title_32` for a date such as "SAT 3 OCT".

Faces cannot bring their own fonts. Keep fixed text to Latin letters, digits and common punctuation: other characters
may not be in the fonts.
