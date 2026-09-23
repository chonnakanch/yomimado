import type { OcrResponse } from "./ocr-types";

const OCR_URL = import.meta.env.VITE_OCR_URL ?? "http://127.0.0.1:8765";

export async function requestOcr(
  imageSource: string | Blob,
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
  const response = await fetch(`${OCR_URL}/api/v1/ocr`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    const errorBody = await response.text().catch(() => "");
    throw new Error(
      `OCR service returned ${response.status}${errorBody ? `: ${errorBody}` : ""}`,
    );
  }
  return (await response.json()) as OcrResponse;
}
