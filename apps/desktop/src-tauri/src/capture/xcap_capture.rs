use std::{
    fs,
    path::PathBuf,
    time::{SystemTime, UNIX_EPOCH},
};

use base64::prelude::*;
use image::ImageEncoder;

use super::{CaptureError, CaptureMetadata, CapturedImage, DisplayInfo, Rectangle, ScreenCapture};

/// Cross-platform implementation. `xcap` remains isolated here so native
/// ScreenCaptureKit / Windows Graphics Capture can replace it without changing commands.
pub struct XcapScreenCapture {
    output_directory: PathBuf,
}

impl XcapScreenCapture {
    pub fn new(output_directory: PathBuf) -> Self {
        Self { output_directory }
    }

    pub fn physical_selection(
        display: &DisplayInfo,
        logical: Rectangle,
    ) -> Result<Rectangle, CaptureError> {
        let logical = logical.normalized();
        if logical.width <= 0.0 || logical.height <= 0.0 {
            return Err(CaptureError::EmptySelection);
        }
        if !display.viewport_width.is_finite()
            || !display.viewport_height.is_finite()
            || display.viewport_width <= 0.0
            || display.viewport_height <= 0.0
        {
            return Err(CaptureError::Unavailable(
                "Invalid selector viewport".into(),
            ));
        }
        let selector = display.selector_physical_bounds;
        let scale_x = selector.width / display.viewport_width;
        let scale_y = selector.height / display.viewport_height;
        let physical = Rectangle {
            x: selector.x + logical.x * scale_x,
            y: selector.y + logical.y * scale_y,
            width: logical.width * scale_x,
            height: logical.height * scale_y,
        };
        let right = physical.x + physical.width;
        let bottom = physical.y + physical.height;
        let display_right = display.physical_bounds.x + display.physical_bounds.width;
        let display_bottom = display.physical_bounds.y + display.physical_bounds.height;
        if physical.x < display.physical_bounds.x
            || physical.y < display.physical_bounds.y
            || right > display_right
            || bottom > display_bottom
        {
            return Err(CaptureError::OutsideDisplay);
        }
        Ok(physical)
    }
}

impl ScreenCapture for XcapScreenCapture {
    fn capture(
        &self,
        display: &DisplayInfo,
        selection_logical: Rectangle,
    ) -> Result<CapturedImage, CaptureError> {
        let physical = Self::physical_selection(display, selection_logical)?;
        let monitors =
            xcap::Monitor::all().map_err(|error| CaptureError::Unavailable(error.to_string()))?;

        let monitor = monitors
            .iter()
            .find(|monitor| {
                monitor.x().ok() == Some(display.physical_bounds.x as i32)
                    && monitor.y().ok() == Some(display.physical_bounds.y as i32)
            })
            .or_else(|| {
                // Some platforms/libraries report logical coordinates
                let logical_x = (display.physical_bounds.x / display.scale_factor).round() as i32;
                let logical_y = (display.physical_bounds.y / display.scale_factor).round() as i32;
                monitors
                    .iter()
                    .find(|m| m.x().ok() == Some(logical_x) && m.y().ok() == Some(logical_y))
            })
            .or_else(|| {
                monitors
                    .iter()
                    .find(|m| m.name().ok().as_deref() == Some(&display.name))
            })
            .or_else(|| {
                if monitors.len() == 1 {
                    monitors.first()
                } else {
                    None
                }
            })
            .ok_or_else(|| {
                CaptureError::Unavailable("The selected display is no longer available".into())
            })?;

        let image = monitor
            .capture_image()
            .map_err(|error| CaptureError::Unavailable(error.to_string()))?;

        // xcap's image size can differ from Tauri's physical monitor size on
        // Retina/scaled displays. Map the measured screen-physical rectangle
        // into the actual captured image rather than assuming the selector
        // begins at the monitor origin.
        let (local_x, width) = crop_axis(
            physical.x - display.physical_bounds.x,
            physical.width,
            display.physical_bounds.width,
            image.width(),
        )?;
        let (local_y, height) = crop_axis(
            physical.y - display.physical_bounds.y,
            physical.height,
            display.physical_bounds.height,
            image.height(),
        )?;

        let crop = image::imageops::crop_imm(&image, local_x, local_y, width, height).to_image();
        fs::create_dir_all(&self.output_directory)
            .map_err(|error| CaptureError::Save(error.to_string()))?;
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis();
        let path = self
            .output_directory
            .join(format!("capture-{timestamp}.png"));

        let mut png_bytes = Vec::new();
        image::codecs::png::PngEncoder::new(&mut png_bytes)
            .write_image(
                crop.as_raw(),
                crop.width(),
                crop.height(),
                image::ExtendedColorType::Rgba8,
            )
            .map_err(|error| CaptureError::Save(error.to_string()))?;

        fs::write(&path, &png_bytes).map_err(|error| CaptureError::Save(error.to_string()))?;
        let data_url = format!(
            "data:image/png;base64,{}",
            BASE64_STANDARD.encode(&png_bytes)
        );

        Ok(CapturedImage {
            image_path: path.to_string_lossy().into_owned(),
            image_data_url: Some(data_url),
            metadata: CaptureMetadata {
                display_id: display.id.clone(),
                display_name: display.name.clone(),
                screen_physical_bounds: display.physical_bounds,
                selection_physical_bounds: physical,
                selection_logical_bounds: selection_logical.normalized(),
                image_width: crop.width(),
                image_height: crop.height(),
                scale_factor: display.scale_factor,
            },
        })
    }
}

fn crop_axis(
    physical_start: f64,
    physical_length: f64,
    display_physical_length: f64,
    image_length: u32,
) -> Result<(u32, u32), CaptureError> {
    if display_physical_length <= 0.0 || image_length == 0 {
        return Err(CaptureError::Unavailable(
            "Invalid display dimensions".into(),
        ));
    }
    let ratio = f64::from(image_length) / display_physical_length;
    let start = (physical_start * ratio)
        .round()
        .clamp(0.0, f64::from(image_length)) as u32;
    let end = ((physical_start + physical_length) * ratio)
        .round()
        .clamp(0.0, f64::from(image_length)) as u32;
    if end <= start {
        return Err(CaptureError::OutsideDisplay);
    }
    Ok((start, end - start))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn physical_selection_at_1x() {
        let display = DisplayInfo {
            id: "disp1".into(),
            name: "Display 1".into(),
            physical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 1920.0,
                height: 1080.0,
            },
            selector_physical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 1920.0,
                height: 1080.0,
            },
            scale_factor: 1.0,
            viewport_width: 1920.0,
            viewport_height: 1080.0,
        };
        let logical = Rectangle {
            x: 100.0,
            y: 50.0,
            width: 400.0,
            height: 200.0,
        };
        let physical = XcapScreenCapture::physical_selection(&display, logical).unwrap();
        assert_eq!((physical.x, physical.y), (100.0, 50.0));
        assert_eq!((physical.width, physical.height), (400.0, 200.0));
    }

    #[test]
    fn physical_selection_at_2x_retina() {
        let display = DisplayInfo {
            id: "disp1".into(),
            name: "Display 1".into(),
            physical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 3840.0,
                height: 2160.0,
            },
            selector_physical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 3840.0,
                height: 2160.0,
            },
            scale_factor: 2.0,
            viewport_width: 1920.0,
            viewport_height: 1080.0,
        };
        let logical = Rectangle {
            x: 100.0,
            y: 50.0,
            width: 400.0,
            height: 200.0,
        };
        let physical = XcapScreenCapture::physical_selection(&display, logical).unwrap();
        assert_eq!((physical.x, physical.y), (200.0, 100.0));
        assert_eq!((physical.width, physical.height), (800.0, 400.0));
    }

    #[test]
    fn physical_selection_with_negative_monitor_offset() {
        let display = DisplayInfo {
            id: "disp2".into(),
            name: "Display 2".into(),
            physical_bounds: Rectangle {
                x: -1920.0,
                y: 0.0,
                width: 1920.0,
                height: 1080.0,
            },
            selector_physical_bounds: Rectangle {
                x: -1920.0,
                y: 0.0,
                width: 1920.0,
                height: 1080.0,
            },
            scale_factor: 1.0,
            viewport_width: 1920.0,
            viewport_height: 1080.0,
        };
        let logical = Rectangle {
            x: 50.0,
            y: 50.0,
            width: 100.0,
            height: 100.0,
        };
        let physical = XcapScreenCapture::physical_selection(&display, logical).unwrap();
        assert_eq!((physical.x, physical.y), (-1870.0, 50.0));
    }

    #[test]
    fn crop_uses_actual_xcap_image_size() {
        assert_eq!(crop_axis(100.0, 400.0, 1920.0, 3840).unwrap(), (200, 800));
        assert_eq!(crop_axis(100.0, 400.0, 1920.0, 1920).unwrap(), (100, 400));
    }

    #[test]
    fn measured_viewport_controls_physical_selection() {
        let display = DisplayInfo {
            id: "disp1".into(),
            name: "Display 1".into(),
            physical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 3000.0,
                height: 2000.0,
            },
            selector_physical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 3000.0,
                height: 2000.0,
            },
            scale_factor: 2.0,
            viewport_width: 2000.0,
            viewport_height: 1000.0,
        };
        let logical = Rectangle {
            x: 100.0,
            y: 50.0,
            width: 200.0,
            height: 100.0,
        };
        let physical = XcapScreenCapture::physical_selection(&display, logical).unwrap();
        assert_eq!((physical.x, physical.y), (150.0, 100.0));
        assert_eq!((physical.width, physical.height), (300.0, 200.0));
    }

    #[test]
    fn selector_inset_below_menu_bar_moves_capture_and_crop_together() {
        let display = DisplayInfo {
            id: "retina".into(),
            name: "Retina".into(),
            physical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 2940.0,
                height: 1912.0,
            },
            selector_physical_bounds: Rectangle {
                x: 0.0,
                y: 66.0,
                width: 2940.0,
                height: 1846.0,
            },
            scale_factor: 2.0,
            viewport_width: 1470.0,
            viewport_height: 923.0,
        };
        let selection = Rectangle {
            x: 600.0,
            y: 300.0,
            width: 100.0,
            height: 150.0,
        };
        let physical = XcapScreenCapture::physical_selection(&display, selection).unwrap();
        assert_eq!(
            (physical.x, physical.y, physical.width, physical.height),
            (1200.0, 666.0, 200.0, 300.0)
        );
        assert_eq!(
            crop_axis(
                physical.y,
                physical.height,
                display.physical_bounds.height,
                1912
            )
            .unwrap(),
            (666, 300)
        );
        assert_eq!(
            crop_axis(
                physical.y,
                physical.height,
                display.physical_bounds.height,
                956
            )
            .unwrap(),
            (333, 150)
        );
    }
}
