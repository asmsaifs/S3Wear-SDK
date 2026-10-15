# Watch face registry

What a `face.json` (face format api 1) can name. Generated from the simulator (`s3w_sim --list-face-registry`), so it is what the watch accepts.

## Bindings

An element's `bind` is one of these. _Text_ is the form a text element shows, _value_ the number a gauge or hand uses. _Updates on_ is the data that makes it redraw.

| Binding | Text | Value | Updates on |
|---|---|---|---|
| `time.hh:mm` | yes | yes | time |
| `time.hh` | yes | yes | time |
| `time.mm` | yes | yes | time |
| `time.ss` | yes | yes | time, second |
| `time.ampm` | yes | yes | time |
| `time.hour` | — | yes | time |
| `time.minute` | — | yes | time, second |
| `time.second` | — | yes | time, second |
| `date.<pattern>` | yes | yes | time |
| `battery.percent` | yes | yes | battery |
| `battery.ratio` | yes | yes | battery |
| `battery.charging` | yes | yes | battery |
| `steps.count` | yes | yes | steps |
| `steps.goal` | yes | yes | steps |
| `steps.goal_ratio` | yes | yes | steps |
| `weather.temp` | yes | yes | weather |
| `weather.low` | yes | yes | weather |
| `weather.high` | yes | yes | weather |
| `weather.condition` | yes | yes | weather |
| `phone.battery` | yes | yes | phone |
| `next_event.title` | yes | — | event |
| `next_event.time` | yes | yes | time, event |
| `heart.bpm` | yes | yes | heart |
| `notifications.count` | yes | yes | notify |
| `moon.phase` | yes | yes | time |
| `moon.illumination` | yes | yes | time |

A `date.<pattern>` binding formats the date with a pattern: `EEEE` (Saturday), `EEE` (Sat), `d` (3), `dd` (03),
`MMMM` (October), `MMM` (Oct), `MM` (10), `M` (10), `yyyy` (2026), `yy` (26). Other letters are invalid, anything else is
copied. The names are English.

## Fonts

| Name |
|---|
| `digits_160` |
| `digits_96` |
| `digits_96_light` |
| `title_32` |
| `body_26` |
| `caption_22` |

## Complications

A slot's `default` complication, and what a tap on it opens.

| Id | Name | Opens | Updates on |
|---|---|---|---|
| `battery` | Battery | `battery` | battery |
| `steps` | Steps | `activity` | steps |
| `date` | Date | `calendar` | time |
| `weather` | Weather | `weather` | weather |
| `next_event` | Next event | `calendar` | time, event |
| `sunrise` | Sunrise/sunset | `weather` | time, sun |
| `world_time` | World time | `world_clock` | time, world |
| `phone_battery` | Phone battery | — | phone |
| `heart_rate` | Heart rate | `heart_rate` | heart |
| `alarm` | Alarm | `alarms` | time, alarm |
| `timer` | Timer | `timer` | time, timer |
| `notifications` | Notifications | `notifications` | notify |
| `moon` | Moon phase | — | time |
