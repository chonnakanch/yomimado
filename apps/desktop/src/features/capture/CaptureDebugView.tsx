import { useLayoutEffect, useRef, useState } from "react";
import type { CaptureMetadata } from "../../lib/coordinates";
import type { OcrResponse, Point } from "../../lib/ocr-types";
import "./capture-debug.css";

function polygonPoints(points: Point[]): string {
  return points.map((point) => `${point.x},${point.y}`).join(" ");
}

export function fitCaptureDebugImage(
  imageWidth: number,
  imageHeight: number,
  availableWidth: number,
  availableHeight: number,
) {
  if (imageWidth <= 0 || imageHeight <= 0) {
    return { width: 0, height: 0 };
  }
  const scale = Math.min(
    1,
    availableWidth / imageWidth,
    availableHeight / imageHeight,
  );
  return {
    width: imageWidth * scale,
    height: imageHeight * scale,
  };
}

interface CaptureDebugViewProps {
  imageDataUrl: string;
  metadata: CaptureMetadata;
  scanSource?: "automatic" | "saved" | "manual";
  response: OcrResponse | null;
  error: string | null;
  onContinue: () => void;
  onCancel: () => void;
}

export function CaptureDebugView({
  imageDataUrl,
  metadata,
  scanSource,
  response,
  error,
  onContinue,
  onCancel,
}: CaptureDebugViewProps) {
  const { imageWidth, imageHeight } = metadata;
  const imageSectionRef = useRef<HTMLElement>(null);
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 });

  useLayoutEffect(() => {
    const section = imageSectionRef.current;
    if (!section) return;

    const observer = new ResizeObserver(([entry]) => {
      if (!entry) return;
      setImageSize(
        fitCaptureDebugImage(
          imageWidth,
          imageHeight,
          entry.contentRect.width,
          entry.contentRect.height,
        ),
      );
    });
    observer.observe(section);
    return () => observer.disconnect();
  }, [imageWidth, imageHeight]);

  return (
    <main className="capture-debug" aria-label="Capture debug preview">
      <div className="capture-debug-panel">
        <header className="capture-debug-header">
          <div>
            <h1>Capture debug</h1>
            <p>
              Review the captured image and recognized text before showing the
              overlay.
            </p>
          </div>
          <div className="capture-debug-actions">
            <button
              className="utility-button utility-button-primary"
              onClick={onContinue}
              disabled={!response}
            >
              Show overlay
            </button>
            <button className="utility-button" onClick={onCancel}>
              Close
            </button>
          </div>
        </header>

        <ul className="capture-debug-legend" aria-label="Geometry legend">
          <li>
            <span className="capture-debug-key final" aria-hidden="true" />
            Final region
          </li>
          <li>
            <span className="capture-debug-key review" aria-hidden="true" />
            Review OCR
          </li>
          <li>
            <span className="capture-debug-key candidate" aria-hidden="true" />
            Detector candidate
          </li>
          <li>
            <span className="capture-debug-key filtered" aria-hidden="true" />
            Filtered
          </li>
        </ul>

        <div className="capture-debug-content">
          <section
            className="capture-debug-image-section"
            aria-label="Captured image"
            tabIndex={0}
            ref={imageSectionRef}
          >
            <div className="capture-debug-image-frame" style={imageSize}>
              <img src={imageDataUrl} alt="Exact captured screen region" />
              {response && (
                <svg
                  aria-label="OCR polygons on captured image"
                  viewBox={`0 0 ${imageWidth} ${imageHeight}`}
                  preserveAspectRatio="none"
                >
                  {response.debug?.detections.map((detection) => (
                    <polygon
                      className={`capture-debug-detector-box${detection.status === "filtered" ? " filtered" : ""}`}
                      key={detection.id}
                      points={polygonPoints(detection.box)}
                    >
                      <title>{`Detector ${detection.id}: ${detection.status}${detection.filterReason ? ` — ${detection.filterReason}` : ""}`}</title>
                    </polygon>
                  ))}
                  {response.regions.map((region) => (
                    <polygon
                      className={`capture-debug-final-region${region.needsReview || region.geometrySource ? " needs-review" : ""}`}
                      key={region.id}
                      points={polygonPoints(region.polygon)}
                    >
                      <title>
                        {region.reviewReason
                          ? `${region.text} — ${region.reviewReason}`
                          : region.text}
                      </title>
                    </polygon>
                  ))}
                </svg>
              )}
            </div>
          </section>

          <section
            className="capture-debug-results"
            aria-label="OCR result"
            tabIndex={0}
          >
            <h2>OCR result</h2>
            <div className="capture-debug-summary">
              <p>
                {imageWidth} × {imageHeight} image px · {metadata.scaleFactor}×
                display scale
              </p>
              <p>Capture held in memory; no PNG saved to disk.</p>
              {scanSource === "automatic" && (
                <p>Automatic manga-page crop used.</p>
              )}
              {scanSource === "saved" && <p>Saved manga-area fallback used.</p>}
            </div>
            {error && (
              <p className="capture-debug-error" role="alert">
                {error}
              </p>
            )}
            {!response && !error && <p role="status">Recognizing text…</p>}
            {response && (
              <>
                <p role="status">
                  Engine: {response.engine} · {response.regions.length}{" "}
                  region(s)
                </p>
                {response.regions.length === 0 && (
                  <p>No text regions detected.</p>
                )}
                <ol>
                  {response.regions.map((region) => (
                    <li key={region.id}>
                      <strong lang="ja">{region.text}</strong>
                      <span>
                        {region.orientation} · confidence:{" "}
                        {region.confidence === 0
                          ? "unknown"
                          : region.confidence.toFixed(2)}
                        {region.geometrySource === "selection" &&
                          " · approximate selected-area box"}
                        {region.geometrySource === "expandedCrop" &&
                          " · approximate crop boundary"}
                        {region.needsReview && " · review suggested"}
                      </span>
                      {region.reviewReason && (
                        <span>{region.reviewReason}</span>
                      )}
                      <details className="capture-debug-geometry">
                        <summary>Geometry</summary>
                        <code>
                          {region.polygon
                            .map((point) => `(${point.x}, ${point.y})`)
                            .join(" ")}
                        </code>
                      </details>
                    </li>
                  ))}
                </ol>
                {response.engine === "manga" && !response.debug && (
                  <p>
                    Detector diagnostics unavailable; restart the OCR service.
                  </p>
                )}
                {response.debug && (
                  <details className="capture-debug-detector-results">
                    <summary>
                      Detector stage · {response.debug.detections.length}{" "}
                      candidates
                    </summary>
                    <p>
                      {response.debug.detections.length} candidate box(es) after
                      duplicate retry boxes are merged. Empty and filtered
                      recognitions are shown here too.
                    </p>
                    {!!response.debug.tileRetryCount && (
                      <p>
                        Tile retry: {response.debug.tileRetryCount} overlapping
                        crop(s).
                      </p>
                    )}
                    {!!response.debug.maskRetryCount && (
                      <p>
                        Text-mask retry: up to {response.debug.maskRetryCount}{" "}
                        tile(s) checked.
                      </p>
                    )}
                    {response.debug.selectionText && (
                      <p>
                        Whole-selection retry: {response.debug.selectionText}
                        {response.debug.selectionFallbackUsed
                          ? " (used with approximate geometry)"
                          : " (not used)"}
                      </p>
                    )}
                    <ol>
                      {response.debug.detections.map((detection) => (
                        <li key={detection.id}>
                          <strong>{detection.id}</strong>
                          <span>
                            {detection.detectionPass === "tile"
                              ? "tile retry"
                              : detection.detectionPass === "mask"
                                ? "text-mask retry"
                                : "full image"}{" "}
                            · {detection.status}
                          </span>
                          <p
                            className="capture-debug-detection-text"
                            lang={detection.text ? "ja" : undefined}
                          >
                            {detection.text || "No text"}
                          </p>
                          {detection.filterReason && (
                            <span>
                              Filtered:{" "}
                              {detection.decisionReason ??
                                detection.filterReason}
                            </span>
                          )}
                          {!detection.filterReason &&
                            detection.decisionReason && (
                              <span>
                                {detection.status === "recognized"
                                  ? "Kept"
                                  : "Reason"}
                                : {detection.decisionReason}
                              </span>
                            )}
                          <code>{polygonPoints(detection.box)}</code>
                          {detection.cropDataUrl && (
                            <img
                              className="capture-debug-crop"
                              src={detection.cropDataUrl}
                              alt={`Crop for ${detection.id}`}
                            />
                          )}
                        </li>
                      ))}
                    </ol>
                  </details>
                )}
              </>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
