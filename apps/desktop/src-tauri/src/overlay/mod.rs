use serde::Serialize;
use tauri::{AppHandle, Manager, PhysicalPosition, PhysicalSize, WebviewUrl, WebviewWindowBuilder};

use crate::capture::CaptureMetadata;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct OverlayLayout {
    window_x: i32,
    window_y: i32,
    window_width: u32,
    window_height: u32,
    content_left: f64,
    content_top: f64,
    content_width: f64,
    content_height: f64,
    toolbar_top: f64,
    toolbar_height: f64,
}

fn layout(metadata: &CaptureMetadata) -> OverlayLayout {
    let selection = &metadata.selection_physical_bounds;
    let screen = &metadata.screen_physical_bounds;
    let scale = if metadata.scale_factor > 0.0 {
        metadata.scale_factor
    } else {
        1.0
    };
    let toolbar = (32.0 * scale).round() as i32;
    let minimum_width = (148.0 * scale).round() as i32;
    let screen_right = (screen.x + screen.width).round() as i32;
    let screen_bottom = (screen.y + screen.height).round() as i32;
    let screen_left = screen.x.round() as i32;
    let screen_top = screen.y.round() as i32;
    let selection_x = selection.x.round() as i32;
    let selection_y = selection.y.round() as i32;
    let selection_width = selection.width.round() as i32;
    let selection_height = selection.height.round() as i32;
    let window_width = selection_width
        .max(minimum_width)
        .min(screen_right - screen_left);
    let window_x = selection_x
        .min(screen_right - window_width)
        .max(screen_left);
    let (window_y, content_top, toolbar_top, window_height) = if selection_y - toolbar >= screen_top
    {
        (
            selection_y - toolbar,
            toolbar,
            0,
            selection_height + toolbar,
        )
    } else if selection_y + selection_height + toolbar <= screen_bottom {
        (selection_y, 0, selection_height, selection_height + toolbar)
    } else {
        // A selection filling the display has no outside gutter.
        (selection_y, 0, 0, selection_height)
    };

    OverlayLayout {
        window_x,
        window_y,
        window_width: window_width as u32,
        window_height: window_height as u32,
        content_left: f64::from(selection_x - window_x) / scale,
        content_top: f64::from(content_top) / scale,
        content_width: f64::from(selection_width) / scale,
        content_height: f64::from(selection_height) / scale,
        toolbar_top: f64::from(toolbar_top) / scale,
        toolbar_height: f64::from(toolbar) / scale,
    }
}

pub fn show_overlay(
    app: &AppHandle,
    metadata: &CaptureMetadata,
    regions: serde_json::Value,
    engine: &str,
) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("ocr-overlay") {
        let _ = window.close();
    }
    let layout = layout(metadata);
    let state = serde_json::json!({ "metadata": metadata, "regions": regions, "engine": engine, "layout": layout });
    let serialized_state = state.to_string();
    let encoded = urlencoding::encode(&serialized_state);
    let window = WebviewWindowBuilder::new(
        app,
        "ocr-overlay",
        WebviewUrl::App(format!("index.html?mode=overlay&state={encoded}").into()),
    )
    .transparent(true)
    .decorations(false)
    .always_on_top(true)
    .skip_taskbar(true)
    .visible(false)
    .build()
    .map_err(|error| error.to_string())?;
    window
        .set_position(PhysicalPosition::new(layout.window_x, layout.window_y))
        .map_err(|error| error.to_string())?;
    window
        .set_size(PhysicalSize::new(layout.window_width, layout.window_height))
        .map_err(|error| error.to_string())?;
    window.show().map_err(|error| error.to_string())?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::capture::Rectangle;

    #[test]
    fn small_selection_gets_toolbar_outside_image() {
        let metadata = CaptureMetadata {
            display_id: "test".into(),
            display_name: "test".into(),
            screen_physical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 1920.0,
                height: 1080.0,
            },
            selection_physical_bounds: Rectangle {
                x: 1800.0,
                y: 300.0,
                width: 40.0,
                height: 70.0,
            },
            selection_logical_bounds: Rectangle {
                x: 900.0,
                y: 150.0,
                width: 20.0,
                height: 35.0,
            },
            image_width: 40,
            image_height: 70,
            scale_factor: 2.0,
        };
        let result = layout(&metadata);
        assert_eq!(result.window_x, 1624);
        assert_eq!(result.content_left, 88.0);
        assert_eq!(result.content_top, 32.0);
        assert_eq!(result.toolbar_top, 0.0);
        assert_eq!(result.content_width, 20.0);
    }

    #[test]
    fn content_stays_on_the_selected_screen_rectangle() {
        let metadata = CaptureMetadata {
            display_id: "retina".into(),
            display_name: "Retina".into(),
            screen_physical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 2940.0,
                height: 1912.0,
            },
            selection_physical_bounds: Rectangle {
                x: 1200.0,
                y: 666.0,
                width: 200.0,
                height: 300.0,
            },
            selection_logical_bounds: Rectangle {
                x: 600.0,
                y: 300.0,
                width: 100.0,
                height: 150.0,
            },
            image_width: 200,
            image_height: 300,
            scale_factor: 2.0,
        };
        let result = layout(&metadata);
        assert_eq!(
            f64::from(result.window_x) + result.content_left * 2.0,
            1200.0
        );
        assert_eq!(f64::from(result.window_y) + result.content_top * 2.0, 666.0);
        assert_eq!(result.content_width * 2.0, 200.0);
        assert_eq!(result.content_height * 2.0, 300.0);
    }
}
