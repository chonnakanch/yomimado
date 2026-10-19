//! A retry owns one region in one completed scan; OCR pixels never replace the scan.
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::capture::{CaptureMetadata, Rectangle};

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RegionTarget {
    pub session_id: u64,
    pub region_id: String,
}

#[derive(Clone)]
pub struct RegionRetry {
    pub target: RegionTarget,
    pub original: Value,
    pub metadata: CaptureMetadata,
    pub area: Rectangle,
}

fn points(region: &Value, metadata: &CaptureMetadata) -> Result<Vec<(f64, f64)>, String> {
    let points = region["polygon"].as_array().ok_or("Missing OCR polygon")?;
    if points.len() < 3 || metadata.image_width == 0 || metadata.image_height == 0 {
        return Err("Invalid OCR region geometry".into());
    }
    points
        .iter()
        .map(|p| {
            let x = p["x"].as_f64().ok_or("Invalid OCR point")?;
            let y = p["y"].as_f64().ok_or("Invalid OCR point")?;
            if !x.is_finite()
                || !y.is_finite()
                || x < 0.0
                || y < 0.0
                || x > f64::from(metadata.image_width)
                || y > f64::from(metadata.image_height)
            {
                return Err("OCR polygon lies outside the captured image".into());
            }
            Ok((x, y))
        })
        .collect()
}

fn image_to_physical(metadata: &CaptureMetadata, point: (f64, f64)) -> (f64, f64) {
    let area = metadata.selection_physical_bounds;
    (
        area.x + point.0 * area.width / f64::from(metadata.image_width),
        area.y + point.1 * area.height / f64::from(metadata.image_height),
    )
}

impl RegionRetry {
    pub fn new(original: Value, target: RegionTarget) -> Result<Self, String> {
        if original["sessionId"].as_u64() != Some(target.session_id)
            || original["engine"] != "manga"
        {
            return Err("This OCR result was replaced. Open the current bubble again.".into());
        }
        let metadata: CaptureMetadata =
            serde_json::from_value(original["metadata"].clone()).map_err(|e| e.to_string())?;
        let region = original["regions"]
            .as_array()
            .and_then(|regions| {
                regions
                    .iter()
                    .find(|r| r["id"].as_str() == Some(&target.region_id))
            })
            .ok_or("This OCR bubble is no longer available")?;
        let polygon = points(region, &metadata)?;
        let left = polygon.iter().map(|p| p.0).fold(f64::INFINITY, f64::min);
        let top = polygon.iter().map(|p| p.1).fold(f64::INFINITY, f64::min);
        let right = polygon
            .iter()
            .map(|p| p.0)
            .fold(f64::NEG_INFINITY, f64::max);
        let bottom = polygon
            .iter()
            .map(|p| p.1)
            .fold(f64::NEG_INFINITY, f64::max);
        let (x, y) = image_to_physical(&metadata, (left, top));
        let (right, bottom) = image_to_physical(&metadata, (right, bottom));
        let area = Rectangle {
            x,
            y,
            width: right - x,
            height: bottom - y,
        };
        let retry = Self {
            target,
            original,
            metadata,
            area,
        };
        retry.validate_area(area)?;
        Ok(retry)
    }

    pub fn validate_area(&self, area: Rectangle) -> Result<(), String> {
        let bounds = self.metadata.selection_physical_bounds;
        if ![
            area.x,
            area.y,
            area.width,
            area.height,
            bounds.x,
            bounds.y,
            bounds.width,
            bounds.height,
        ]
        .iter()
        .all(|n| n.is_finite())
            || area.width <= 0.0
            || area.height <= 0.0
            || bounds.width <= 0.0
            || bounds.height <= 0.0
            || area.x < bounds.x - 0.001
            || area.y < bounds.y - 0.001
            || area.x + area.width > bounds.x + bounds.width + 0.001
            || area.y + area.height > bounds.y + bounds.height + 0.001
        {
            return Err("Redraw one bubble inside the original scanned area. The previous OCR result was kept.".into());
        }
        Ok(())
    }

    pub fn merge(&self, captured: &CaptureMetadata, regions: Value) -> Result<Value, String> {
        self.validate_area(captured.selection_physical_bounds)?;
        if captured.display_id != self.metadata.display_id
            || captured.scale_factor != self.metadata.scale_factor
        {
            return Err("The retry display changed. Scan the page again.".into());
        }
        let replacements = regions.as_array().ok_or("Invalid retry OCR response")?;
        if replacements.len() != 1
            || replacements[0]["text"]
                .as_str()
                .is_none_or(|s| s.trim().is_empty())
        {
            return Err("Retry needs one recognized text region. Redraw tightly around one bubble; the previous result was kept.".into());
        }
        let mut replacement = replacements[0].clone();
        if !matches!(
            replacement["orientation"].as_str(),
            Some("horizontal" | "vertical")
        ) || !matches!(
            replacement["type"].as_str(),
            Some("dialogue" | "narration" | "soundEffect" | "other")
        ) || replacement["tokens"].as_array().is_none()
        {
            return Err("Invalid retry OCR region fields; the previous result was kept.".into());
        }
        let polygon = points(&replacement, captured)?;
        let original_area = self.metadata.selection_physical_bounds;
        replacement["polygon"] = polygon.into_iter().map(|point| {
            let (x,y) = image_to_physical(captured, point);
            serde_json::json!({"x": (x-original_area.x) * f64::from(self.metadata.image_width) / original_area.width,
                               "y": (y-original_area.y) * f64::from(self.metadata.image_height) / original_area.height})
        }).collect::<Vec<_>>().into();
        replacement["id"] = self.target.region_id.clone().into();
        // A rerun is not proof of accuracy: Manga OCR exposes no calibrated score.
        replacement["confidence"] = 0.into();
        replacement["needsReview"] = true.into();
        let reason = replacement["reviewReason"]
            .as_str()
            .filter(|s| !s.is_empty())
            .unwrap_or(
                "Bubble OCR retried; recognition confidence is unavailable. Verify on the page.",
            )
            .to_string();
        replacement["reviewReason"] = reason.into();
        let mut original = self.original["regions"]
            .as_array()
            .ok_or("Previous OCR regions are unavailable")?
            .clone();
        let index = original
            .iter()
            .position(|r| r["id"].as_str() == Some(&self.target.region_id))
            .ok_or("The original bubble is unavailable")?;
        original[index] = replacement;
        Ok(original.into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn snapshot(scale: f64) -> Value {
        json!({"sessionId": 7, "engine":"manga", "estimatedReadingOrder":true,
        "metadata": {"displayId":"left", "displayName":"Left", "scaleFactor":scale,
          "screenPhysicalBounds":{"x":-1920.0*scale,"y":0,"width":1920.0*scale,"height":1080.0*scale},
          "selectionPhysicalBounds":{"x":-1600.0*scale,"y":100.0*scale,"width":600.0*scale,"height":400.0*scale},
          "selectionLogicalBounds":{"x":0,"y":0,"width":600,"height":400},"imageWidth":1200,"imageHeight":800},
        "regions":[
          {"id":"bubble", "text":"old", "polygon":[{"x":200,"y":100},{"x":400,"y":100},{"x":400,"y":300},{"x":200,"y":300}]},
          {"id":"keep", "text":"unchanged", "polygon":[{"x":700,"y":100},{"x":800,"y":100},{"x":800,"y":300}],"tokens":[],"orientation":"vertical","confidence":0,"type":"other"}
        ]})
    }
    fn retry(scale: f64) -> RegionRetry {
        RegionRetry::new(
            snapshot(scale),
            RegionTarget {
                session_id: 7,
                region_id: "bubble".into(),
            },
        )
        .unwrap()
    }
    fn replacement() -> Value {
        json!({"id":"region-1","text":"新しい","polygon":[{"x":10,"y":20},{"x":190,"y":20},{"x":190,"y":180},{"x":10,"y":180}],"orientation":"vertical","confidence":1,"type":"dialogue","tokens":[]})
    }
    fn captured(retry: &RegionRetry) -> CaptureMetadata {
        CaptureMetadata {
            selection_physical_bounds: retry.area,
            image_width: 200,
            image_height: 200,
            ..retry.metadata.clone()
        }
    }

    #[test]
    fn maps_one_retried_polygon_through_physical_pixels_and_keeps_all_other_regions() {
        for scale in [1.0, 1.25, 1.5, 2.0] {
            let retry = retry(scale);
            assert_eq!(retry.area.x, -1500.0 * scale);
            assert_eq!(retry.area.y, 150.0 * scale);
            assert_eq!(retry.area.width, 100.0 * scale);
            let result = retry
                .merge(&captured(&retry), json!([replacement()]))
                .unwrap();
            assert_eq!(result[0]["id"], "bubble");
            assert_eq!(result[0]["text"], "新しい");
            assert_eq!(result[0]["polygon"][0], json!({"x":210.0,"y":120.0}));
            assert_eq!(result[0]["polygon"][2], json!({"x":390.0,"y":280.0}));
            assert_eq!(result[1], retry.original["regions"][1]);
            assert_eq!(result[0]["confidence"], 0);
            assert_eq!(result[0]["needsReview"], true);
            assert!(result[0]["reviewReason"]
                .as_str()
                .unwrap()
                .contains("confidence is unavailable"));
            assert_eq!(retry.original["regions"][0]["text"], "old");
        }
    }

    #[test]
    fn translates_redrawn_bounds_and_different_capture_image_sizes() {
        let retry = retry(1.5);
        let mut capture = captured(&retry);
        capture.selection_physical_bounds.x += 30.0;
        capture.image_width = 100;
        let mut region = replacement();
        region["polygon"] = json!([{"x":0,"y":0},{"x":100,"y":0},{"x":100,"y":200}]);
        let result = retry.merge(&capture, json!([region])).unwrap();
        assert_eq!(result[0]["polygon"][0], json!({"x":240.0,"y":100.0}));
        assert_eq!(result[0]["polygon"][2], json!({"x":440.0,"y":300.0}));
    }

    #[test]
    fn rejects_stale_missing_and_demo_targets() {
        for (id, region) in [(6, "bubble"), (7, "missing")] {
            assert!(RegionRetry::new(
                snapshot(1.0),
                RegionTarget {
                    session_id: id,
                    region_id: region.into()
                }
            )
            .is_err());
        }
        let mut demo = snapshot(1.0);
        demo["engine"] = "demo".into();
        assert!(RegionRetry::new(
            demo,
            RegionTarget {
                session_id: 7,
                region_id: "bubble".into()
            }
        )
        .is_err());
    }

    #[test]
    fn empty_multiple_or_invalid_replies_cannot_replace_the_original() {
        let retry = retry(1.0);
        let mut invalid = replacement();
        invalid["text"] = " ".into();
        let mut outside = replacement();
        outside["polygon"][0]["x"] = (-1).into();
        let mut bad_fields = replacement();
        bad_fields["tokens"] = Value::Null;
        for regions in [
            json!([]),
            json!([replacement(), replacement()]),
            json!([invalid]),
            json!([outside]),
            json!([bad_fields]),
        ] {
            assert!(retry.merge(&captured(&retry), regions).is_err());
            assert_eq!(retry.original["regions"][0]["text"], "old");
        }
    }

    #[test]
    fn rejects_changed_displays_and_redraws_outside_the_original_scan() {
        let retry = retry(2.0);
        let mut capture = captured(&retry);
        capture.selection_physical_bounds.x = 0.0;
        assert!(retry.merge(&capture, json!([replacement()])).is_err());
        capture = captured(&retry);
        capture.display_id = "other".into();
        assert!(retry.merge(&capture, json!([replacement()])).is_err());
        capture = captured(&retry);
        capture.scale_factor = 1.0;
        assert!(retry.merge(&capture, json!([replacement()])).is_err());
        capture = captured(&retry);
        capture.selection_physical_bounds.width = f64::NAN;
        assert!(retry.merge(&capture, json!([replacement()])).is_err());
    }
}
