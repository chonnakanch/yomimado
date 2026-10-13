const SERVICE_URL = import.meta.env.VITE_OCR_URL ?? "http://127.0.0.1:8765";

/** Keep transport errors separate from each endpoint's response validation. */
export async function requestService(
  path: string,
  service: string,
  options?: RequestInit,
): Promise<Response> {
  const headers = new Headers(options?.headers);
  // Forces browser preflight even for multipart uploads and read-only APIs.
  headers.set("X-YomiMado-Client", "desktop");
  const response = await fetch(`${SERVICE_URL}${path}`, {
    ...options,
    headers: Object.fromEntries(headers.entries()),
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail =
      body !== null &&
      typeof body === "object" &&
      "detail" in body &&
      typeof body.detail === "string" &&
      body.detail.trim()
        ? body.detail
        : `${service} returned ${response.status}`;
    throw new Error(detail);
  }
  return response;
}

export async function postServiceJson(
  path: string,
  service: string,
  body: unknown,
): Promise<unknown> {
  const response = await requestService(path, service, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return response.json();
}
