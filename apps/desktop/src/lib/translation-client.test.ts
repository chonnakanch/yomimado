import { afterEach, describe, expect, it, vi } from "vitest";
import { requestTranslation } from "./translation-client";

afterEach(() => vi.unstubAllGlobals());

describe("requestTranslation", () => {
  it("sends only explicitly supplied text to the local service", async () => {
    const fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          sourceText: "学校",
          translatedText: "School",
          provider: "test-local-model",
          cached: false,
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetch);

    const result = await requestTranslation(" 学校 ");
    expect(result.translatedText).toBe("School");
    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8765/api/v1/translate",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ text: "学校" }),
      }),
    );
  });

  it("does not send blank text", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    await expect(requestTranslation("   ")).rejects.toThrow(
      "Enter Japanese text",
    );
    expect(fetch).not.toHaveBeenCalled();
  });
});
