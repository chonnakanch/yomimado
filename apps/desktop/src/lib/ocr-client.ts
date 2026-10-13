import type { OcrResponse } from "./ocr-types";
import { parseOcrResponse } from "./ocr-response";
import { requestService } from "./service-client";

export async function requestOcr(
  imageSource: string | Blob,
  options: { debug?: boolean } = {},
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
      const image = await fetch(imageSource);
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
  });
  return parseOcrResponse(await response.json());
}
