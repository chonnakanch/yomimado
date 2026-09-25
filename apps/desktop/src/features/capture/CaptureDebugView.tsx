import type { CaptureMetadata } from "../../lib/coordinates";
import type { OcrResponse } from "../../lib/ocr-types";

interface CaptureDebugViewProps {
  imageDataUrl: string;
  imagePath: string;
  metadata: CaptureMetadata;
  response: OcrResponse | null;
  error: string | null;
  onContinue: () => void;
  onCancel: () => void;
}

export function CaptureDebugView({
  imageDataUrl,
  imagePath,
  metadata,
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
              Exact PNG sent to OCR, with returned polygons in image pixels.
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
                  {response.regions.map((region) => (
                    <polygon
                      key={region.id}
                      points={region.polygon
                        .map((point) => `${point.x},${point.y}`)
                        .join(" ")}
                    >
                      <title>{region.text}</title>
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
            <p className="capture-debug-path">Saved locally: {imagePath}</p>
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
                      </span>
                      <code>
                        {region.polygon
                          .map((point) => `(${point.x}, ${point.y})`)
                          .join(" ")}
                      </code>
                    </li>
                  ))}
                </ol>
              </>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
