import { afterEach, expect, it, vi } from "vitest";
import { postServiceJson, requestService } from "./service-client";

afterEach(() => vi.unstubAllGlobals());

it("sends JSON to the local service and returns untrusted data for endpoint validation", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify({ entries: [] })));
  vi.stubGlobal("fetch", fetch);
  await expect(
    postServiceJson("/api/v1/word", "Word lookup", { surface: "学校" }),
  ).resolves.toEqual({ entries: [] });
  expect(fetch).toHaveBeenCalledWith("http://127.0.0.1:8765/api/v1/word", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ surface: "学校" }),
  });
});

it("preserves service setup error details", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ detail: "Install the local dictionary" }),
          { status: 503 },
        ),
      ),
  );
  await expect(requestService("/api/v1/word", "Word lookup")).rejects.toThrow(
    "Install the local dictionary",
  );
});

it.each([
  "service unavailable",
  "null",
  JSON.stringify({
    detail: [{ loc: ["body", "text"], msg: "Field required" }],
  }),
  JSON.stringify({ detail: 42 }),
  JSON.stringify({ detail: "  " }),
])(
  "uses the HTTP status when error details are malformed: %s",
  async (body) => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(body, { status: 422 })),
    );
    await expect(
      requestService("/api/v1/translate", "Translation service"),
    ).rejects.toThrow("Translation service returned 422");
  },
);

it("does not parse a successful empty DELETE response", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
  );
  const response = await requestService(
    "/api/v1/sentences/7",
    "Sentence service",
    { method: "DELETE" },
  );
  expect(response.status).toBe(204);
  expect(response.bodyUsed).toBe(false);
});
