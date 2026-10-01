import type { CaptureMetadata } from "../../lib/coordinates";
import type { OcrResponse, Point } from "../../lib/ocr-types";

function polygonPoints(points: Point[]): string {
  return points.map((point) => `${point.x},${point.y}`).join(" ");
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

  return (
    <main className="capture-debug">
      <div className="capture-debug-panel">
        <header className="capture-debug-header">
          <div>
            <h1>Capture debug</h1>
            <p>
              Exact PNG sent to OCR. Orange: final regions; dashed gold: review
              suggested; cyan: detector candidates; gray: filtered boxes.
            </p>
          </div>
          <div className="capture-debug-actions">
            <button onClick={onContinue} disabled={!response}>
              Show overlay
            </button>
            <button className="capture-debug-secondary" onClick={onCancel}>
              Close
            </button>
          </div>
        </header>

        <div className="capture-debug-content">
          <section
            className="capture-debug-image-section"
            aria-label="Captured image"
          >
            <div
              className="capture-debug-image-frame"
              style={{ aspectRatio: `${imageWidth} / ${imageHeight}` }}
            >
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
                      className={`capture-debug-final-region${region.needsReview ? " needs-review" : ""}`}
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

          <section className="capture-debug-results" aria-label="OCR result">
            <h2>OCR result</h2>
            <p>
              {imageWidth} × {imageHeight} image px · {metadata.scaleFactor}×
              display scale
            </p>
            <p>Capture held in memory; no PNG saved to disk.</p>
            {scanSource === "automatic" && (
              <p>Automatic manga-page crop used.</p>
            )}
            {scanSource === "saved" && <p>Saved manga-area fallback used.</p>}
            {error && <p className="capture-debug-error">{error}</p>}
            {!response && !error && <p>Recognizing text…</p>}
            {response && (
              <>
                <p>
                  Engine: {response.engine} · {response.regions.length}{" "}
                  region(s)
                </p>
                {response.regions.length === 0 && (
                  <p>No text regions detected.</p>
                )}
                <ol>
                  {response.regions.map((region) => (
                    <li key={region.id}>
                      <strong>{region.text}</strong>
                      <span>
                        {region.orientation} · confidence:{" "}
                        {region.confidence === 0
                          ? "unknown"
                          : region.confidence.toFixed(2)}
                        {region.geometrySource === "selection" &&
                          " · approximate selected-area box"}
                        {region.needsReview && " · review suggested"}
                      </span>
                      {region.reviewReason && (
                        <span>{region.reviewReason}</span>
                      )}
                      <code>
                        {region.polygon
                          .map((point) => `(${point.x}, ${point.y})`)
                          .join(" ")}
                      </code>
                    </li>
                  ))}
                </ol>
                {response.engine === "manga" && !response.debug && (
                  <p>
                    Detector diagnostics unavailable; restart the OCR service.
                  </p>
                )}
                {response.debug && (
                  <section className="capture-debug-detector-results">
                    <h2>Detector stage</h2>
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
                            · {detection.status} · {detection.text || "No text"}
                          </span>
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
                  </section>
                )}
              </>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
