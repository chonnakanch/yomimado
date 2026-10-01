use base64::prelude::*;
use image::{imageops::FilterType, ImageEncoder, RgbaImage};

use super::{CaptureError, CapturedImage, Rectangle};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct PixelBounds {
    x: u32,
    y: u32,
    width: u32,
    height: u32,
}

fn paper(pixel: &image::Rgba<u8>) -> bool {
    let [r, g, b, _] = pixel.0;
    r >= 220 && g >= 220 && b >= 220 && r.max(g).max(b) - r.min(g).min(b) <= 22
}

fn ink(pixel: &image::Rgba<u8>) -> bool {
    let [r, g, b, _] = pixel.0;
    r <= 90 && g <= 90 && b <= 90
}

fn trailing_dark_toolbar_start(
    sample: &RgbaImage,
    left: u32,
    right: u32,
    page_top: u32,
) -> Option<u32> {
    let sample_height = sample.height();
    let span_width = usize::try_from(right - left + 1).ok()?;
    let row_counts = |y| {
        (left..=right).fold((0usize, 0usize), |(white, dark), x| {
            let pixel = sample.get_pixel(x, y);
            (
                white + usize::from(paper(pixel)),
                dark + usize::from(ink(pixel)),
            )
        })
    };
    let mut start = sample_height;
    while start > page_top {
        let (white, dark) = row_counts(start - 1);
        if white * 100 > span_width * 8 || dark * 100 < span_width * 70 {
            break;
        }
        start -= 1;
    }
    let band_height = sample_height - start;
    let body_height = sample_height - page_top;
    if band_height < (sample_height / 48).max(3)
        || band_height > (sample_height / 9).max(4)
        || start < page_top + body_height / 2
    {
        return None;
    }
    // A page edge is a sharp transition from light paper to a persistent dark
    // strip. A dark final manga panel should not be cropped on this evidence.
    let has_light_edge = start.saturating_sub(2)..start;
    has_light_edge
        .filter(|&y| y >= page_top)
        .any(|y| row_counts(y).0 * 100 >= span_width * 35)
        .then_some(start)
}

fn has_scattered_toolbar_marks(
    image: &RgbaImage,
    sample: &RgbaImage,
    left: u32,
    right: u32,
    band_start: u32,
) -> bool {
    // Text and icons disappear in the small page-detection sample. Check the
    // original pixels for several separated light marks in the dark strip;
    // an unmarked black manga panel is not enough evidence to trim it.
    let x1 = left * image.width() / sample.width();
    let x2 = ((right + 1) * image.width()).div_ceil(sample.width());
    let y1 = band_start * image.height() / sample.height();
    let band_width = x2.saturating_sub(x1);
    if band_width < 4 || y1 >= image.height() {
        return false;
    }
    let mut bright = [0usize; 4];
    let mut total = [0usize; 4];
    for y in y1..image.height() {
        for x in x1..x2.min(image.width()) {
            let bin = (((x - x1) * 4 / band_width).min(3)) as usize;
            total[bin] += 1;
            let [r, g, b, _] = image.get_pixel(x, y).0;
            bright[bin] += usize::from(r >= 160 && g >= 160 && b >= 160);
        }
    }
    (0..4)
        .filter(|&bin| total[bin] > 0 && bright[bin] * 200 >= total[bin])
        .count()
        >= 3
}

/// A deliberately conservative first pass for black-and-white manga pages.
/// Ambiguous or light-themed layouts return None so the saved area can be used.
fn detect_page_bounds(image: &RgbaImage) -> Option<PixelBounds> {
    let (width, height) = image.dimensions();
    if width < 320 || height < 240 {
        return None;
    }
    let ratio = (256.0 / f64::from(width.max(height))).min(1.0);
    let sample_width = (f64::from(width) * ratio).round().max(1.0) as u32;
    let sample_height = (f64::from(height) * ratio).round().max(1.0) as u32;
    let sample = image::imageops::resize(image, sample_width, sample_height, FilterType::Triangle);

    let top_probe = (sample_height / 20).max(4);
    let initial_paper = (0..top_probe)
        .flat_map(|y| (0..sample_width).map(move |x| (x, y)))
        .filter(|&(x, y)| paper(sample.get_pixel(x, y)))
        .count();
    if initial_paper * 100 >= (top_probe * sample_width) as usize * 3 {
        return None;
    }

    let max_start = (sample_height * 3 / 10).max(top_probe + 4);
    let first_paper_row = (top_probe..max_start.min(sample_height - 3)).find(|&start| {
        let count = (start..start + 3)
            .flat_map(|y| (0..sample_width).map(move |x| (x, y)))
            .filter(|&(x, y)| paper(sample.get_pixel(x, y)))
            .count();
        count * 100 >= (3 * sample_width) as usize * 10
    })?;
    let sample_top = first_paper_row;

    let body_height = sample_height - sample_top;
    // Use one continuous page-like span, not the first and last pale pixels on
    // the entire screen. Sparse text and thumbnails in a dark website sidebar
    // must not extend a manga crop across the intervening UI.
    let page_columns: Vec<u32> = (0..sample_width)
        .filter(|&x| {
            let white = (sample_top..sample_height)
                .filter(|&y| paper(sample.get_pixel(x, y)))
                .count();
            white * 100 >= body_height as usize * 18
        })
        .collect();
    let max_internal_gap = (sample_width / 12).max(2);
    let mut spans = Vec::new();
    let mut start = *page_columns.first()?;
    let mut end = start;
    for &column in page_columns.iter().skip(1) {
        if column - end > max_internal_gap + 1 {
            spans.push((start, end));
            start = column;
        }
        end = column;
    }
    spans.push((start, end));
    spans.sort_by_key(|&(start, end)| end - start);
    let &(left, right) = spans.last()?;
    if right - left < sample_width * 25 / 100 {
        return None;
    }
    if spans
        .iter()
        .rev()
        .nth(1)
        .is_some_and(|&(start, end)| end - start >= (right - left) * 3 / 4)
    {
        return None;
    }

    let mut white = 0usize;
    let mut dark = 0usize;
    for y in sample_top..sample_height {
        for x in left..=right {
            let pixel = sample.get_pixel(x, y);
            white += usize::from(paper(pixel));
            dark += usize::from(ink(pixel));
        }
    }
    let area = usize::try_from((right - left + 1) * body_height).ok()?;
    // Fine line art can contain little solid-black ink after downsampling.
    if white * 100 < area * 12 || dark * 100 < area * 4 {
        return None;
    }

    let sample_bottom = trailing_dark_toolbar_start(&sample, left, right, sample_top)
        .filter(|&start| has_scattered_toolbar_marks(image, &sample, left, right, start))
        .unwrap_or(sample_height);
    let pad_x = (sample_width / 50).max(2);
    let sample_left = left.saturating_sub(pad_x);
    let sample_right = (right + pad_x + 1).min(sample_width);
    let x = (f64::from(sample_left) * f64::from(width) / f64::from(sample_width)).floor() as u32;
    let y = (f64::from(sample_top) * f64::from(height) / f64::from(sample_height)).floor() as u32;
    let right =
        (f64::from(sample_right) * f64::from(width) / f64::from(sample_width)).ceil() as u32;
    let bottom =
        (f64::from(sample_bottom) * f64::from(height) / f64::from(sample_height)).ceil() as u32;
    Some(PixelBounds {
        x,
        y,
        width: right.min(width) - x,
        height: bottom.min(height) - y,
    })
}

fn crop_metadata(capture: &mut CapturedImage, bounds: PixelBounds) {
    let image_width = f64::from(capture.metadata.image_width);
    let image_height = f64::from(capture.metadata.image_height);
    let physical = capture.metadata.selection_physical_bounds;
    let logical = capture.metadata.selection_logical_bounds;
    let fraction = Rectangle {
        x: f64::from(bounds.x) / image_width,
        y: f64::from(bounds.y) / image_height,
        width: f64::from(bounds.width) / image_width,
        height: f64::from(bounds.height) / image_height,
    };
    capture.metadata.selection_physical_bounds = Rectangle {
        x: physical.x + fraction.x * physical.width,
        y: physical.y + fraction.y * physical.height,
        width: fraction.width * physical.width,
        height: fraction.height * physical.height,
    };
    capture.metadata.selection_logical_bounds = Rectangle {
        x: logical.x + fraction.x * logical.width,
        y: logical.y + fraction.y * logical.height,
        width: fraction.width * logical.width,
        height: fraction.height * logical.height,
    };
    capture.metadata.image_width = bounds.width;
    capture.metadata.image_height = bounds.height;
}

pub fn crop_detected_page(
    mut capture: CapturedImage,
) -> Result<Option<CapturedImage>, CaptureError> {
    let encoded = capture
        .image_data_url
        .split_once(',')
        .ok_or_else(|| CaptureError::Unavailable("Invalid capture data URL".into()))?
        .1;
    let bytes = BASE64_STANDARD
        .decode(encoded)
        .map_err(|error| CaptureError::Unavailable(error.to_string()))?;
    let image = image::load_from_memory_with_format(&bytes, image::ImageFormat::Png)
        .map_err(|error| CaptureError::Unavailable(error.to_string()))?
        .to_rgba8();
    let Some(bounds) = detect_page_bounds(&image) else {
        return Ok(None);
    };
    let crop = image::imageops::crop_imm(&image, bounds.x, bounds.y, bounds.width, bounds.height)
        .to_image();
    let mut png = Vec::new();
    image::codecs::png::PngEncoder::new(&mut png)
        .write_image(
            crop.as_raw(),
            crop.width(),
            crop.height(),
            image::ExtendedColorType::Rgba8,
        )
        .map_err(|error| CaptureError::Encode(error.to_string()))?;
    crop_metadata(&mut capture, bounds);
    capture.image_data_url = format!("data:image/png;base64,{}", BASE64_STANDARD.encode(png));
    Ok(Some(capture))
}

#[cfg(test)]
mod tests {
    use image::{Rgba, RgbaImage};

    use super::*;
    use crate::capture::CaptureMetadata;

    fn comic_screen() -> RgbaImage {
        let mut image = RgbaImage::from_pixel(1000, 600, Rgba([40, 40, 40, 255]));
        for y in 100..600 {
            for x in 100..900 {
                image.put_pixel(x, y, Rgba([250, 250, 250, 255]));
            }
        }
        for x in (130..870).step_by(40) {
            for y in 130..580 {
                for offset in 0..12 {
                    image.put_pixel(x + offset, y, Rgba([20, 20, 20, 255]));
                }
            }
        }
        image
    }

    #[test]
    fn finds_a_large_black_and_white_page_below_dark_browser_chrome() {
        let bounds = detect_page_bounds(&comic_screen()).unwrap();
        assert!(bounds.x <= 100 && bounds.x + bounds.width >= 900);
        assert!(bounds.y >= 60 && bounds.y <= 110);
        assert_eq!(bounds.height + bounds.y, 600);
    }

    #[test]
    fn stops_before_a_short_dark_site_toolbar_below_the_page() {
        let mut screen = comic_screen();
        for y in 540..600 {
            for x in 100..900 {
                screen.put_pixel(x, y, Rgba([10, 10, 10, 255]));
            }
        }
        // Sparse white engagement icons and counts should not make the strip
        // look like another manga panel.
        for x in [200, 400, 600, 800] {
            for y in 555..570 {
                for offset in 0..10 {
                    screen.put_pixel(x + offset, y, Rgba([245, 245, 245, 255]));
                }
            }
        }

        let bounds = detect_page_bounds(&screen).unwrap();
        assert!(bounds.y + bounds.height >= 530);
        assert!(bounds.y + bounds.height <= 545);
    }

    #[test]
    fn keeps_a_short_dark_final_panel_without_toolbar_marks() {
        let mut screen = comic_screen();
        for y in 540..600 {
            for x in 100..900 {
                screen.put_pixel(x, y, Rgba([10, 10, 10, 255]));
            }
        }
        let bounds = detect_page_bounds(&screen).unwrap();
        assert_eq!(bounds.y + bounds.height, 600);
    }

    #[test]
    fn keeps_a_tall_dark_final_manga_panel() {
        let mut screen = comic_screen();
        for y in 400..600 {
            for x in 100..900 {
                screen.put_pixel(x, y, Rgba([10, 10, 10, 255]));
            }
        }
        let bounds = detect_page_bounds(&screen).unwrap();
        assert_eq!(bounds.y + bounds.height, 600);
    }

    #[test]
    fn refuses_a_light_webpage_and_a_dark_toolbar_without_manga() {
        let mut webpage = RgbaImage::from_pixel(1000, 600, Rgba([250, 250, 250, 255]));
        for y in 0..100 {
            for x in 0..1000 {
                webpage.put_pixel(x, y, Rgba([40, 40, 40, 255]));
            }
        }
        assert!(detect_page_bounds(&webpage).is_none());
        let toolbar = RgbaImage::from_pixel(1000, 600, Rgba([40, 40, 40, 255]));
        assert!(detect_page_bounds(&toolbar).is_none());
    }

    #[test]
    fn excludes_sparse_white_text_and_thumbnail_in_a_dark_sidebar() {
        let mut screen = RgbaImage::from_pixel(1000, 600, Rgba([30, 30, 30, 255]));
        for y in 100..600 {
            for x in 250..650 {
                screen.put_pixel(x, y, Rgba([250, 250, 250, 255]));
            }
        }
        for x in (275..625).step_by(40) {
            for y in 130..580 {
                for offset in 0..12 {
                    screen.put_pixel(x + offset, y, Rgba([20, 20, 20, 255]));
                }
            }
        }
        for y in [140, 210, 280] {
            for line_y in y..y + 12 {
                for x in 770..980 {
                    screen.put_pixel(x, line_y, Rgba([250, 250, 250, 255]));
                }
            }
        }
        for y in 420..485 {
            for x in 790..860 {
                screen.put_pixel(x, y, Rgba([250, 250, 250, 255]));
            }
        }

        let bounds = detect_page_bounds(&screen).unwrap();
        assert!(bounds.x <= 250);
        assert!(bounds.x + bounds.width >= 650);
        assert!(bounds.x + bounds.width < 770);
    }

    #[test]
    fn finds_a_narrow_page_with_light_line_art_beside_dark_site_ui() {
        let mut screen = RgbaImage::from_pixel(1000, 600, Rgba([30, 30, 30, 255]));
        for y in 100..600 {
            for x in 300..580 {
                screen.put_pixel(x, y, Rgba([250, 250, 250, 255]));
            }
        }
        for x in [330, 390, 450, 510] {
            for y in 150..550 {
                for offset in 0..6 {
                    screen.put_pixel(x + offset, y, Rgba([20, 20, 20, 255]));
                }
            }
        }
        for y in [160, 230, 300] {
            for line_y in y..y + 10 {
                for x in 800..980 {
                    screen.put_pixel(x, line_y, Rgba([250, 250, 250, 255]));
                }
            }
        }

        let bounds = detect_page_bounds(&screen).unwrap();
        assert!(bounds.x <= 300);
        assert!(bounds.x + bounds.width >= 580);
        assert!(bounds.x + bounds.width < 800);
    }

    #[test]
    fn refuses_two_similarly_sized_page_like_spans() {
        let mut screen = RgbaImage::from_pixel(1000, 600, Rgba([30, 30, 30, 255]));
        for y in 100..600 {
            for x in 100..390 {
                screen.put_pixel(x, y, Rgba([250, 250, 250, 255]));
            }
            for x in 610..900 {
                screen.put_pixel(x, y, Rgba([250, 250, 250, 255]));
            }
        }
        for x in (120..380).chain(630..890).step_by(35) {
            for y in 130..580 {
                for offset in 0..10 {
                    screen.put_pixel(x + offset, y, Rgba([20, 20, 20, 255]));
                }
            }
        }
        assert!(detect_page_bounds(&screen).is_none());
    }

    #[test]
    fn cropping_preserves_physical_and_logical_geometry() {
        let mut capture = CapturedImage {
            image_data_url: String::new(),
            metadata: CaptureMetadata {
                display_id: "retina".into(),
                display_name: "Retina".into(),
                screen_physical_bounds: Rectangle {
                    x: 0.0,
                    y: 0.0,
                    width: 2000.0,
                    height: 1200.0,
                },
                selection_physical_bounds: Rectangle {
                    x: 0.0,
                    y: 100.0,
                    width: 2000.0,
                    height: 1200.0,
                },
                selection_logical_bounds: Rectangle {
                    x: 0.0,
                    y: 0.0,
                    width: 1000.0,
                    height: 600.0,
                },
                image_width: 1000,
                image_height: 600,
                scale_factor: 2.0,
            },
        };
        crop_metadata(
            &mut capture,
            PixelBounds {
                x: 100,
                y: 75,
                width: 800,
                height: 525,
            },
        );
        assert_eq!(capture.metadata.selection_physical_bounds.x, 200.0);
        assert_eq!(capture.metadata.selection_physical_bounds.y, 250.0);
        assert_eq!(capture.metadata.selection_physical_bounds.width, 1600.0);
        assert_eq!(capture.metadata.selection_logical_bounds.y, 75.0);
        assert_eq!(capture.metadata.image_width, 800);
    }

    #[test]
    fn detected_crop_is_the_png_sent_to_ocr() {
        let image = comic_screen();
        let mut png = Vec::new();
        image::codecs::png::PngEncoder::new(&mut png)
            .write_image(
                image.as_raw(),
                image.width(),
                image.height(),
                image::ExtendedColorType::Rgba8,
            )
            .unwrap();
        let capture = CapturedImage {
            image_data_url: format!("data:image/png;base64,{}", BASE64_STANDARD.encode(png)),
            metadata: CaptureMetadata {
                display_id: "screen".into(),
                display_name: "Screen".into(),
                screen_physical_bounds: Rectangle {
                    x: 0.0,
                    y: 0.0,
                    width: 2000.0,
                    height: 1200.0,
                },
                selection_physical_bounds: Rectangle {
                    x: 0.0,
                    y: 0.0,
                    width: 2000.0,
                    height: 1200.0,
                },
                selection_logical_bounds: Rectangle {
                    x: 0.0,
                    y: 0.0,
                    width: 1000.0,
                    height: 600.0,
                },
                image_width: 1000,
                image_height: 600,
                scale_factor: 2.0,
            },
        };
        let cropped = crop_detected_page(capture).unwrap().unwrap();
        let encoded = cropped.image_data_url.split_once(',').unwrap().1;
        let bytes = BASE64_STANDARD.decode(encoded).unwrap();
        let decoded = image::load_from_memory(&bytes).unwrap();
        assert_eq!(decoded.width(), cropped.metadata.image_width);
        assert_eq!(decoded.height(), cropped.metadata.image_height);
        assert!(cropped.metadata.selection_physical_bounds.y > 0.0);
        assert!(cropped.metadata.image_width < 1000);
    }
}
