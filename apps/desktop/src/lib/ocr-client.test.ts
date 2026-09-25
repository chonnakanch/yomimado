import { afterEach, expect, it, vi } from "vitest";
import { requestOcr } from "./ocr-client";

afterEach(() => vi.unstubAllGlobals());

it("requests detector diagnostics only in capture debug mode", async () => {
  const fetch = vi.fn().mockImplementation(() =>
    Promise.resolve(
      new Response(JSON.stringify({ regions: [], engine: "demo" }), {
        status: 200,
      }),
    ),
  );
  vi.stubGlobal("fetch", fetch);
  const image = new Blob(["test image"], { type: "image/png" });

  await requestOcr(image, { debug: true });
  const debugForm = fetch.mock.calls[0][1].body as FormData;
  expect(debugForm.get("debug")).toBe("true");
  expect(debugForm.get("image")).toBeInstanceOf(Blob);

  await requestOcr(image);
  const normalForm = fetch.mock.calls[1][1].body as FormData;
  expect(normalForm.has("debug")).toBe(false);
});
