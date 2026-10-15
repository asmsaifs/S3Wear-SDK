//! {{name}}: a counter that survives restarts (the S3Wear Rust template, api_level 1).
//!
//!   s3w build .     -> build/app.wasm and build/{{id}}.s3app
//!   s3w run-sim .   -> the simulator, rebuilt and reloaded on every save
//!
//! A `no_std` cdylib: the lifecycle functions below are the app's exports. Callbacks must return
//! within 50 ms (s3w_on_start: 250 ms). The developer docs have the API and the rules.
#![no_std]

use s3w::sys::*;
use s3w::{kv, ui};

s3w::export_event_buf!();

// The app runs on one thread: plain statics, read and written only from the callbacks.
static mut COUNT: i32 = 0;
static mut COUNT_LABEL: ui::Handle = 0;
static mut PLUS: ui::Handle = 0;
static mut RESET: ui::Handle = 0;

fn show() {
    let mut buf = [0u8; 12];
    unsafe { ui::set_text(COUNT_LABEL, s3w::fmt_i32(&mut buf, COUNT)) };
}

#[no_mangle]
pub extern "C" fn s3w_on_start() {
    s3w::info("{{name}} started");
    unsafe { COUNT = kv::get_i32("count").unwrap_or(0) };
    let scr = ui::screen();
    ui::set_style(scr, S3W_STYLE_FLEX, S3W_FLEX_COLUMN);
    ui::set_style(scr, S3W_STYLE_PAD, 40);
    ui::set_style(scr, S3W_STYLE_GAP, 16);
    if let Ok(title) = ui::label(scr, "{{name}}") {
        ui::set_style(title, S3W_STYLE_FONT, S3W_FONT_TITLE);
    }
    let count = ui::label(scr, "0").unwrap_or(0);
    ui::set_style(count, S3W_STYLE_FONT, S3W_FONT_DISPLAY);
    let plus = ui::button(scr, "+1").unwrap_or(0);
    ui::set_size(plus, 200, S3W_SIZE_CONTENT);
    let reset = ui::button(scr, "Reset").unwrap_or(0);
    ui::set_size(reset, 200, S3W_SIZE_CONTENT);
    unsafe {
        COUNT_LABEL = count;
        PLUS = plus;
        RESET = reset;
    }
    show();
}

#[no_mangle]
pub extern "C" fn s3w_on_event(e: &s3w::Event) {
    if e.r#type != S3W_EV_CLICK {
        return;
    }
    unsafe {
        if e.handle == PLUS {
            COUNT += 1;
        } else if e.handle == RESET {
            COUNT = 0;
        }
        let _ = kv::set_i32("count", COUNT); // app-private storage
    }
    show();
}
