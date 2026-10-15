import { afterEach, expect, it, vi } from "vitest";
import { OCR_TIMEOUT_MS, requestOcr } from "./ocr-client";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

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
  expect(fetch.mock.calls[0][1].headers).toEqual({
    "x-yomimado-client": "desktop",
  });

  await requestOcr(image);
  const normalForm = fetch.mock.calls[1][1].body as FormData;
  expect(normalForm.has("debug")).toBe(false);
});

it("rejects malformed service data before capture can display it", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ regions: [{ text: "学校" }], engine: "manga" }),
        ),
      ),
  );
  await expect(
    requestOcr(new Blob(["image"], { type: "image/png" })),
  ).rejects.toThrow("OCR service returned invalid data");
});

it.each(["upload", "body"])(
  "aborts a stalled OCR %s and ignores a response arriving after the deadline",
  async (stage) => {
    vi.useFakeTimers();
    let resolveUpload!: (response: Response) => void;
    let resolveBody!: (body: unknown) => void;
    const upload = new Promise<Response>((resolve) => {
      resolveUpload = resolve;
    });
    const body = new Promise<unknown>((resolve) => {
      resolveBody = resolve;
    });
    const fetch = vi
      .fn()
      .mockReturnValue(
        stage === "upload"
          ? upload
          : Promise.resolve({ ok: true, json: () => body }),
      );
    vi.stubGlobal("fetch", fetch);
    const outcome = requestOcr(
      new Blob(["image"], { type: "image/png" }),
    ).catch((error: unknown) => error);
    const signal = fetch.mock.calls[0][1].signal as AbortSignal;
    await vi.advanceTimersByTimeAsync(OCR_TIMEOUT_MS - 1);
    expect(signal.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    const failure = await outcome;
    expect(failure).toBeInstanceOf(Error);
    expect((failure as Error).message).toContain(
      "OCR timed out after 3 minutes",
    );
    expect(signal.aborted).toBe(true);
    const response = { engine: "manga", regions: [] };
    resolveUpload(new Response(JSON.stringify(response)));
    resolveBody(response);
    await vi.runAllTimersAsync();
    expect(await outcome).toBe(failure);
    expect(vi.getTimerCount()).toBe(0);
  },
);

it("clears its deadline after a successful OCR response", async () => {
  vi.useFakeTimers();
  const fetch = vi
    .fn()
    .mockResolvedValue(
      new Response(JSON.stringify({ engine: "manga", regions: [] })),
    );
  vi.stubGlobal("fetch", fetch);
  await expect(
    requestOcr(new Blob(["image"], { type: "image/png" })),
  ).resolves.toEqual({ engine: "manga", regions: [] });
  expect(vi.getTimerCount()).toBe(0);
  await vi.advanceTimersByTimeAsync(OCR_TIMEOUT_MS);
  expect((fetch.mock.calls[0][1].signal as AbortSignal).aborted).toBe(false);
});
