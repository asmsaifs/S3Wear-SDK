//! Safe wrappers over the S3Wear mini app API (`sdk/include/s3w.h`, api_level 1) for `no_std`
//! wasm32 apps. The raw imports are in [`sys`]; this crate covers what most apps need. Every app
//! calls [`export_event_buf!`] once and defines the lifecycle exports it uses
//! (`#[no_mangle] pub extern "C" fn s3w_on_start()`, `s3w_on_event`, `s3w_on_frame`, ...).
#![no_std]

pub use s3w_sys as sys;

/// An event passed to `s3w_on_event` (`S3W_EV_*` in `sys`).
pub type Event = sys::s3w_event_t;

/// Error code from the API (`sys::S3W_ERR_*`).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Error(pub i32);

fn check(r: i32) -> Result<i32, Error> {
    if r >= 0 {
        Ok(r)
    } else {
        Err(Error(r))
    }
}

/// Defines the `s3w_event_buf` export the runtime writes each event to. Call once in the app.
#[macro_export]
macro_rules! export_event_buf {
    () => {
        #[no_mangle]
        pub extern "C" fn s3w_event_buf() -> *mut $crate::Event {
            static mut EV: $crate::Event = $crate::Event {
                r#type: 0,
                handle: 0,
                value: 0,
                x: 0,
                y: 0,
                reserved: [0; 3],
            };
            unsafe { core::ptr::addr_of_mut!(EV) }
        }
    };
}

/// A panic traps the app (the watch shows "App stopped").
#[cfg(target_arch = "wasm32")]
#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    core::arch::wasm32::unreachable()
}

fn len(s: &[u8]) -> i32 {
    s.len() as i32
}

// --- System ------------------------------------------------------------------------------------

pub fn log(level: i32, msg: &str) {
    unsafe { sys::s3w_log(level, msg.as_ptr(), len(msg.as_bytes())) }
}

pub fn info(msg: &str) {
    log(sys::S3W_LOG_INFO, msg)
}

/// Milliseconds since the app started.
pub fn millis() -> u32 {
    unsafe { sys::s3w_millis() }
}

/// Ends the app at once.
pub fn exit() {
    unsafe { sys::s3w_exit() }
}

/// A timer (≥ 20 ms, ≤ 8 at once): `S3W_EV_TIMER` with the returned id.
pub fn timer_start(period_ms: u32, repeat: bool) -> Result<i32, Error> {
    check(unsafe { sys::s3w_timer_start(period_ms, repeat) })
}

pub fn timer_stop(id: i32) {
    unsafe { sys::s3w_timer_stop(id) }
}

/// Formats an integer into buf, returning the text (no allocator in `no_std` apps).
pub fn fmt_i32(buf: &mut [u8; 12], v: i32) -> &str {
    let mut n = (v as i64).unsigned_abs();
    let mut i = buf.len();
    loop {
        i -= 1;
        buf[i] = b'0' + (n % 10) as u8;
        n /= 10;
        if n == 0 {
            break;
        }
    }
    if v < 0 {
        i -= 1;
        buf[i] = b'-';
    }
    core::str::from_utf8(&buf[i..]).unwrap_or("")
}

// --- Widgets mode ------------------------------------------------------------------------------

pub mod ui {
    use super::{check, len, sys, Error};

    /// A widget handle.
    pub type Handle = i32;

    pub fn screen() -> Handle {
        unsafe { sys::s3w_ui_screen() }
    }
    pub fn label(parent: Handle, text: &str) -> Result<Handle, Error> {
        check(unsafe { sys::s3w_ui_label(parent, text.as_ptr(), len(text.as_bytes())) })
    }
    /// `S3W_EV_CLICK` with its handle.
    pub fn button(parent: Handle, text: &str) -> Result<Handle, Error> {
        check(unsafe { sys::s3w_ui_button(parent, text.as_ptr(), len(text.as_bytes())) })
    }
    pub fn set_text(h: Handle, text: &str) {
        unsafe { sys::s3w_ui_set_text(h, text.as_ptr(), len(text.as_bytes())) }
    }
    pub fn set_value(h: Handle, v: i32) {
        unsafe { sys::s3w_ui_set_value(h, v) }
    }
    pub fn set_pos(h: Handle, x: i32, y: i32) {
        unsafe { sys::s3w_ui_set_pos(h, x, y) }
    }
    pub fn set_size(h: Handle, w: i32, hgt: i32) {
        unsafe { sys::s3w_ui_set_size(h, w, hgt) }
    }
    /// prop is `sys::S3W_STYLE_*`.
    pub fn set_style(h: Handle, prop: i32, value: i32) {
        unsafe { sys::s3w_ui_set_style(h, prop, value) }
    }
    pub fn delete(h: Handle) {
        unsafe { sys::s3w_ui_delete(h) }
    }
    pub fn toast(text: &str) {
        unsafe { sys::s3w_ui_toast(text.as_ptr(), len(text.as_bytes())) }
    }
}

// --- Canvas mode -------------------------------------------------------------------------------

pub mod gfx {
    use super::{len, sys};

    /// RGB565 from 8-bit channels.
    pub const fn rgb565(r: u8, g: u8, b: u8) -> u16 {
        ((r as u16 & 0xF8) << 8) | ((g as u16 & 0xFC) << 3) | (b as u16 >> 3)
    }
    pub fn set_fps(fps: i32) {
        unsafe { sys::s3w_gfx_set_fps(fps) }
    }
    pub fn clear(color: u16) {
        unsafe { sys::s3w_gfx_clear(color) }
    }
    pub fn rect(x: i32, y: i32, w: i32, h: i32, color: u16, fill: bool) {
        unsafe { sys::s3w_gfx_rect(x, y, w, h, color, fill) }
    }
    pub fn circle(cx: i32, cy: i32, r: i32, color: u16, fill: bool) {
        unsafe { sys::s3w_gfx_circle(cx, cy, r, color, fill) }
    }
    pub fn line(x0: i32, y0: i32, x1: i32, y1: i32, color: u16, width: i32) {
        unsafe { sys::s3w_gfx_line(x0, y0, x1, y1, color, width) }
    }
    /// font is `sys::S3W_FONT_*`.
    pub fn text(x: i32, y: i32, t: &str, font: i32, color: u16) {
        unsafe { sys::s3w_gfx_text(x, y, t.as_ptr(), len(t.as_bytes()), font, color) }
    }
    pub fn text_width(t: &str, font: i32) -> i32 {
        unsafe { sys::s3w_gfx_text_width(t.as_ptr(), len(t.as_bytes()), font) }
    }
    pub fn present() {
        unsafe { sys::s3w_gfx_present() }
    }
}

// --- Storage -----------------------------------------------------------------------------------

pub mod kv {
    use super::{check, len, sys, Error};

    /// Copies the value into buf; returns its full length.
    pub fn get(key: &str, buf: &mut [u8]) -> Result<usize, Error> {
        check(unsafe {
            sys::s3w_kv_get(key.as_ptr(), len(key.as_bytes()), buf.as_mut_ptr().cast(), len(buf))
        })
        .map(|n| n as usize)
    }
    pub fn set(key: &str, value: &[u8]) -> Result<(), Error> {
        check(unsafe {
            sys::s3w_kv_set(key.as_ptr(), len(key.as_bytes()), value.as_ptr().cast(), len(value))
        })
        .map(|_| ())
    }
    pub fn delete(key: &str) -> Result<(), Error> {
        check(unsafe { sys::s3w_kv_delete(key.as_ptr(), len(key.as_bytes())) }).map(|_| ())
    }
    /// An i32 stored as 4 little-endian bytes.
    pub fn get_i32(key: &str) -> Option<i32> {
        let mut b = [0u8; 4];
        match get(key, &mut b) {
            Ok(4) => Some(i32::from_le_bytes(b)),
            _ => None,
        }
    }
    pub fn set_i32(key: &str, v: i32) -> Result<(), Error> {
        set(key, &v.to_le_bytes())
    }
}

/// Game services (P8-08): high scores kept in the app's storage, and random numbers.
pub mod game {
    use super::{check, sys, Error};

    /// Records score on board (0..8) if it beats the best (higher wins; `lower`: lower wins, for
    /// times). Ok(true) for a new best.
    pub fn submit(board: i32, score: i32, lower: bool) -> Result<bool, Error> {
        let b = if lower { board | sys::S3W_HIGHSCORE_LOWER } else { board };
        check(unsafe { sys::s3w_highscore_submit(b, score) }).map(|r| r == 1)
    }
    /// The board's best, or None before the first score.
    pub fn best(board: i32) -> Option<i32> {
        let mut v = 0i32;
        match unsafe { sys::s3w_highscore_get(board, &mut v) } {
            0 => Some(v),
            _ => None,
        }
    }
    /// 0..=0x7FFF_FFFF from the watch's hardware RNG.
    pub fn random() -> i32 {
        unsafe { sys::s3w_random() }
    }
}
