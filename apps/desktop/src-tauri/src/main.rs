// Release builds are GUI applications; the OCR child is hidden independently.
#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

fn main() {
    yomimado_lib::run()
}
