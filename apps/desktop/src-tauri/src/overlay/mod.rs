use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri::{AppHandle, Manager, PhysicalPosition, PhysicalSize, WebviewUrl, WebviewWindowBuilder};

use crate::capture::{CaptureMetadata, Rectangle};

const POPUP_LOGICAL_WIDTH: f64 = 460.0;
const INITIAL_POPUP_LOGICAL_HEIGHT: f64 = 320.0;
const POPUP_SCREEN_INSET: f64 = 12.0;
const OVERLAY_URL: &str = "index.html?mode=overlay";

#[derive(Default)]
pub struct OverlayStore(Mutex<Option<serde_json::Value>>);

impl OverlayStore {
    fn set(&self, value: serde_json::Value) -> Result<(), String> {
        *self.0.lock().map_err(|error| error.to_string())? = Some(value);
        Ok(())
    }

    pub fn get(&self) -> Result<serde_json::Value, String> {
        self.0
            .lock()
            .map_err(|error| error.to_string())?
            .clone()
            .ok_or_else(|| "OCR overlay data is unavailable".into())
    }

    pub fn clear(&self) -> Result<(), String> {
        *self.0.lock().map_err(|error| error.to_string())? = None;
        Ok(())
    }
}

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

#[derive(Clone, Copy, Deserialize)]
pub struct OcrPoint {
    x: f64,
    y: f64,
}

#[derive(Debug, PartialEq)]
struct PopupPosition {
    x: i32,
    y: i32,
    width: u32,
    height: u32,
}

#[derive(Clone, Copy, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PopupPlacement {
    screen: Rectangle,
    anchor_left: f64,
    anchor_right: f64,
    anchor_top: f64,
    scale_factor: f64,
}

fn popup_placement(
    metadata: &CaptureMetadata,
    polygon: &[OcrPoint],
    screen: Rectangle,
) -> Result<PopupPlacement, String> {
    if polygon.len() < 3 || metadata.image_width == 0 || metadata.image_height == 0 {
        return Err("The selected OCR region has no usable geometry".into());
    }
    let scale = metadata.scale_factor;
    if !scale.is_finite() || scale <= 0.0 {
        return Err("Invalid display scale".into());
    }
    let min_x = polygon
        .iter()
        .map(|point| point.x)
        .fold(f64::INFINITY, f64::min);
    let max_x = polygon
        .iter()
        .map(|point| point.x)
        .fold(f64::NEG_INFINITY, f64::max);
    let min_y = polygon
        .iter()
        .map(|point| point.y)
        .fold(f64::INFINITY, f64::min);
    if !min_x.is_finite() || !max_x.is_finite() || !min_y.is_finite() {
        return Err("Invalid OCR region coordinates".into());
    }
    let selection = metadata.selection_physical_bounds;
    let anchor_left = selection.x + min_x * selection.width / f64::from(metadata.image_width);
    let anchor_right = selection.x + max_x * selection.width / f64::from(metadata.image_width);
    let anchor_top = selection.y + min_y * selection.height / f64::from(metadata.image_height);
    Ok(PopupPlacement {
        screen,
        anchor_left,
        anchor_right,
        anchor_top,
        scale_factor: scale,
    })
}

fn popup_position(placement: PopupPlacement, logical_height: f64) -> Result<PopupPosition, String> {
    let screen = placement.screen;
    let scale = placement.scale_factor;
    if !logical_height.is_finite()
        || logical_height <= 0.0
        || !scale.is_finite()
        || scale <= 0.0
        || !screen.width.is_finite()
        || !screen.height.is_finite()
        || screen.width <= 0.0
        || screen.height <= 0.0
    {
        return Err("Invalid popup size or display bounds".into());
    }
    let inset = (POPUP_SCREEN_INSET * scale)
        .round()
        .min((screen.width.min(screen.height) / 4.0).floor());
    let available_width = (screen.width - 2.0 * inset).max(1.0);
    let available_height = (screen.height - 2.0 * inset).max(1.0);
    let width = (POPUP_LOGICAL_WIDTH * scale).round().min(available_width);
    let height = (logical_height * scale)
        .round()
        .min(available_height)
        .max(1.0);
    let gap = (8.0 * scale).round();
    let screen_left = screen.x + inset;
    let screen_top = screen.y + inset;
    let screen_right = screen.x + screen.width - inset;
    let screen_bottom = screen.y + screen.height - inset;
    let x = if placement.anchor_right + gap + width <= screen_right {
        placement.anchor_right + gap
    } else if placement.anchor_left - gap - width >= screen_left {
        placement.anchor_left - gap - width
    } else {
        (placement.anchor_right + gap).clamp(screen_left, screen_right - width)
    };
    let y = placement
        .anchor_top
        .clamp(screen_top, screen_bottom - height);
    Ok(PopupPosition {
        x: x.round() as i32,
        y: y.round() as i32,
        width: width as u32,
        height: height as u32,
    })
}

fn translation_popup_query(text: &str, demo: bool, placement: PopupPlacement) -> String {
    let state = serde_json::json!({ "text": text, "demo": demo, "placement": placement });
    let serialized = state.to_string();
    let encoded = urlencoding::encode(&serialized);
    format!("mode=translation&state={encoded}")
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
    let fills_visible_display = selection_width >= screen_right - screen_left - 1
        && selection_y + selection_height >= screen_bottom - 1;
    let (window_y, content_top, toolbar_top, window_height) = if fills_visible_display {
        // A macOS selector can start below the menu bar. Placing the toolbar
        // above it would make the OS shift the overlay window down and drift
        // every OCR polygon away from the captured image.
        (selection_y, 0, 0, selection_height)
    } else if selection_y - toolbar >= screen_top {
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
    store: &OverlayStore,
    metadata: &CaptureMetadata,
    regions: serde_json::Value,
    engine: &str,
) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("translation-popup") {
        let _ = window.close();
    }
    if let Some(window) = app.get_webview_window("ocr-overlay") {
        let _ = window.close();
    }
    let layout = layout(metadata);
    let state = serde_json::json!({ "metadata": metadata, "regions": regions, "engine": engine, "layout": layout });
    store.set(state)?;
    let window = WebviewWindowBuilder::new(app, "ocr-overlay", WebviewUrl::App(OVERLAY_URL.into()))
        .transparent(true)
        .decorations(false)
        .always_on_top(true)
        .accept_first_mouse(true)
        .skip_taskbar(true)
        .visible(false)
        .build()
        .map_err(|error| {
            let _ = store.clear();
            error.to_string()
        })?;
    let result = (|| {
        window
            .set_position(PhysicalPosition::new(layout.window_x, layout.window_y))
            .map_err(|error| error.to_string())?;
        window
            .set_size(PhysicalSize::new(layout.window_width, layout.window_height))
            .map_err(|error| error.to_string())?;
        window.show().map_err(|error| error.to_string())
    })();
    if result.is_err() {
        let _ = window.close();
        let _ = store.clear();
    }
    result
}

pub fn show_translation_popup(
    app: &AppHandle,
    metadata: &CaptureMetadata,
    text: &str,
    polygon: &[OcrPoint],
    demo: bool,
) -> Result<(), String> {
    let screen = app
        .get_webview_window("ocr-overlay")
        .and_then(|window| window.current_monitor().ok().flatten())
        .map(|monitor| {
            let area = monitor.work_area();
            Rectangle {
                x: f64::from(area.position.x),
                y: f64::from(area.position.y),
                width: f64::from(area.size.width),
                height: f64::from(area.size.height),
            }
        })
        .unwrap_or(metadata.screen_physical_bounds);
    let placement = popup_placement(metadata, polygon, screen)?;
    let position = popup_position(placement, INITIAL_POPUP_LOGICAL_HEIGHT)?;
    let query = translation_popup_query(text, demo, placement);
    if let Some(window) = app.get_webview_window("translation-popup") {
        // Reuse the existing webview: close() can return before its label is
        // removed, so immediately rebuilding with the same label can fail.
        let mut url = window.url().map_err(|error| error.to_string())?;
        url.set_query(Some(&query));
        window.navigate(url).map_err(|error| error.to_string())?;
        window
            .set_position(PhysicalPosition::new(position.x, position.y))
            .map_err(|error| error.to_string())?;
        window
            .set_size(PhysicalSize::new(position.width, position.height))
            .map_err(|error| error.to_string())?;
        window.show().map_err(|error| error.to_string())?;
        window.set_focus().map_err(|error| error.to_string())?;
        return Ok(());
    }
    let window = WebviewWindowBuilder::new(
        app,
        "translation-popup",
        WebviewUrl::App(format!("index.html?{query}").into()),
    )
    .transparent(true)
    .decorations(false)
    .always_on_top(true)
    .accept_first_mouse(true)
    .skip_taskbar(true)
    .visible(false)
    .build()
    .map_err(|error| error.to_string())?;
    window
        .set_position(PhysicalPosition::new(position.x, position.y))
        .map_err(|error| error.to_string())?;
    window
        .set_size(PhysicalSize::new(position.width, position.height))
        .map_err(|error| error.to_string())?;
    window.show().map_err(|error| error.to_string())?;
    window.set_focus().map_err(|error| error.to_string())?;
    Ok(())
}

pub fn resize_translation_popup(
    app: &AppHandle,
    placement: PopupPlacement,
    logical_height: f64,
) -> Result<(), String> {
    let window = app
        .get_webview_window("translation-popup")
        .ok_or("Translation popup is unavailable")?;
    let position = popup_position(placement, logical_height)?;
    window
        .set_size(PhysicalSize::new(position.width, position.height))
        .map_err(|error| error.to_string())?;
    window
        .set_position(PhysicalPosition::new(position.x, position.y))
        .map_err(|error| error.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::capture::Rectangle;

    #[test]
    fn large_ocr_state_is_kept_out_of_the_webview_url() {
        let store = OverlayStore::default();
        let regions: Vec<_> = (0..300)
            .map(|id| serde_json::json!({ "id": id, "text": "日本語".repeat(100) }))
            .collect();
        store
            .set(serde_json::json!({ "regions": regions }))
            .unwrap();

        assert_eq!(OVERLAY_URL, "index.html?mode=overlay");
        assert_eq!(
            store.get().unwrap()["regions"].as_array().unwrap().len(),
            300
        );
        store.clear().unwrap();
        assert!(store.get().is_err());
    }

    #[test]
    fn translation_popup_navigation_preserves_new_ocr_text() {
        let placement = PopupPlacement {
            screen: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 1920.0,
                height: 1080.0,
            },
            anchor_left: 100.0,
            anchor_right: 200.0,
            anchor_top: 100.0,
            scale_factor: 1.0,
        };
        let mut url = tauri::Url::parse("http://localhost:1420/index.html?mode=translation")
            .expect("valid app URL");
        url.set_query(Some(&translation_popup_query(
            "たまにはいいでしょ",
            false,
            placement,
        )));

        let state = url
            .query_pairs()
            .find(|(key, _)| key == "state")
            .map(|(_, value)| value.into_owned())
            .expect("popup state");
        let state: serde_json::Value = serde_json::from_str(&state).expect("JSON popup state");
        assert_eq!(state["text"], "たまにはいいでしょ");
        assert_eq!(state["demo"], false);
        assert_eq!(state["placement"]["anchorLeft"], 100.0);
    }

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

    #[test]
    fn display_scan_keeps_overlay_below_mac_menu_bar() {
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
                x: 0.0,
                y: 66.0,
                width: 2940.0,
                height: 1846.0,
            },
            selection_logical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 1470.0,
                height: 923.0,
            },
            image_width: 2940,
            image_height: 1846,
            scale_factor: 2.0,
        };
        let result = layout(&metadata);
        assert_eq!(result.window_y, 66);
        assert_eq!(result.content_top, 0.0);
        assert_eq!(result.window_height, 1846);
    }

    #[test]
    fn translation_popup_is_anchored_beside_ocr_region() {
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
        let polygon = [
            OcrPoint { x: 0.0, y: 0.0 },
            OcrPoint { x: 200.0, y: 0.0 },
            OcrPoint { x: 200.0, y: 300.0 },
        ];
        let placement = popup_placement(&metadata, &polygon, metadata.screen_physical_bounds)
            .expect("valid popup placement");
        assert_eq!(
            popup_position(placement, INITIAL_POPUP_LOGICAL_HEIGHT).unwrap(),
            PopupPosition {
                x: 1416,
                y: 666,
                width: 920,
                height: 640
            }
        );
    }

    #[test]
    fn tall_popup_fits_work_area_and_keeps_retina_scale() {
        let placement = PopupPlacement {
            screen: Rectangle {
                x: -1600.0,
                y: 30.0,
                width: 1600.0,
                height: 900.0,
            },
            anchor_left: -200.0,
            anchor_right: -100.0,
            anchor_top: 700.0,
            scale_factor: 2.0,
        };
        let position = popup_position(placement, 800.0).unwrap();
        assert_eq!(position.width, 920);
        assert_eq!(position.height, 852);
        assert!(position.x >= -1576);
        assert!(position.x + position.width as i32 <= -24);
        assert!(position.y >= 54);
        assert!(position.y + position.height as i32 <= 906);
    }

    #[test]
    fn popup_grows_to_content_height_when_screen_has_room() {
        let placement = PopupPlacement {
            screen: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 1920.0,
                height: 1080.0,
            },
            anchor_left: 100.0,
            anchor_right: 200.0,
            anchor_top: 120.0,
            scale_factor: 1.0,
        };
        let position = popup_position(placement, 680.0).unwrap();
        assert_eq!((position.width, position.height), (460, 680));
        assert_eq!((position.x, position.y), (208, 120));
    }

    #[test]
    fn small_screen_clamps_popup_width_and_height() {
        let placement = PopupPlacement {
            screen: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 360.0,
                height: 500.0,
            },
            anchor_left: 200.0,
            anchor_right: 250.0,
            anchor_top: 200.0,
            scale_factor: 1.0,
        };
        let position = popup_position(placement, 900.0).unwrap();
        assert_eq!((position.width, position.height), (336, 476));
        assert_eq!((position.x, position.y), (12, 12));
    }
}
