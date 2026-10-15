import type { OcrResponse } from "./ocr-types";
import { parseOcrResponse } from "./ocr-response";
import { requestService } from "./service-client";

// Allow cold CPU model initialization, but never spin indefinitely on a stalled
// upload, service reply or response body. This applies to both capture modes.
export const OCR_TIMEOUT_MS = 180_000;

export async function requestOcr(
  imageSource: string | Blob,
  options: { debug?: boolean } = {},
): Promise<OcrResponse> {
  const controller = new AbortController();
  let deadline: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    deadline = setTimeout(() => {
      reject(
        new Error(
          "OCR timed out after 3 minutes. Check the local OCR service and try again.",
        ),
      );
      controller.abort();
    }, OCR_TIMEOUT_MS);
  });
  try {
    return await Promise.race([
      recognize(imageSource, options, controller.signal),
      timeout,
    ]);
  } finally {
    clearTimeout(deadline);
  }
}

async function recognize(
  imageSource: string | Blob,
  options: { debug?: boolean },
  signal: AbortSignal,
): Promise<OcrResponse> {
  let blob: Blob;
  if (typeof imageSource === "string") {
    if (imageSource.startsWith("data:")) {
      const commaIndex = imageSource.indexOf(",");
      const base64Data = imageSource.slice(commaIndex + 1);
      const byteCharacters = atob(base64Data);
      const byteNumbers = new Uint8Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      blob = new Blob([byteNumbers], { type: "image/png" });
    } else {
      const image = await fetch(imageSource, { signal });
      if (!image.ok) {
        throw new Error(`Could not read captured image (${image.status})`);
      }
      blob = await image.blob();
    }
  } else {
    blob = imageSource;
  }

  const form = new FormData();
  form.append("image", blob, "capture.png");
  if (options.debug) form.append("debug", "true");
  const response = await requestService("/api/v1/ocr", "OCR service", {
    method: "POST",
    body: form,
    signal,
  });
  return parseOcrResponse(await response.json());
}
