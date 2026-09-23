mod xcap_capture;

use serde::{Deserialize, Serialize};
use thiserror::Error;

pub use xcap_capture::XcapScreenCapture;

#[derive(Debug, Clone, Copy, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Rectangle {
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub height: f64,
}

impl Rectangle {
    pub fn normalized(self) -> Self {
        let x = if self.width < 0.0 {
            self.x + self.width
        } else {
            self.x
        };
        let y = if self.height < 0.0 {
            self.y + self.height
        } else {
            self.y
        };
        Self {
            x,
            y,
            width: self.width.abs(),
            height: self.height.abs(),
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DisplayInfo {
    pub id: String,
    pub name: String,
    pub physical_bounds: Rectangle,
    pub scale_factor: f64,
    /// CSS pixel size of the selector webview, measured by the frontend.
    pub viewport_width: f64,
    pub viewport_height: f64,
}

#[derive(Debug, Clone, Copy, Deserialize)]
pub struct ViewportSize {
    pub width: f64,
    pub height: f64,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CaptureMetadata {
    pub display_id: String,
    pub display_name: String,
    pub screen_physical_bounds: Rectangle,
    pub selection_physical_bounds: Rectangle,
    pub selection_logical_bounds: Rectangle,
    pub image_width: u32,
    pub image_height: u32,
    pub scale_factor: f64,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CapturedImage {
    pub image_path: String,
    pub image_data_url: Option<String>,
    pub metadata: CaptureMetadata,
}

#[derive(Debug, Error)]
pub enum CaptureError {
    #[error("Screen capture is unavailable: {0}")]
    Unavailable(String),
    #[error("The selection must have a positive width and height")]
    EmptySelection,
    #[error("The selection lies outside the active display")]
    OutsideDisplay,
    #[error("Could not save the captured image: {0}")]
    Save(String),
}

pub trait ScreenCapture: Send + Sync {
    fn capture(
        &self,
        display: &DisplayInfo,
        selection_logical: Rectangle,
    ) -> Result<CapturedImage, CaptureError>;
}

#[cfg(test)]
mod tests {
    use super::Rectangle;

    #[test]
    fn normalizes_a_reverse_drag() {
        let rectangle = Rectangle {
            x: 100.0,
            y: 80.0,
            width: -40.0,
            height: -20.0,
        }
        .normalized();
        assert_eq!(
            (rectangle.x, rectangle.y, rectangle.width, rectangle.height),
            (60.0, 60.0, 40.0, 20.0)
        );
    }

    #[test]
    fn keeps_negative_monitor_origins() {
        let rectangle = Rectangle {
            x: -1920.0,
            y: 50.0,
            width: 200.0,
            height: 100.0,
        }
        .normalized();
        assert_eq!(rectangle.x, -1920.0);
    }
}
