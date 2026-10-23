import { useEffect, useState } from "react";
import type { TextRegion } from "../../lib/ocr-types";
import { requestTranslation } from "../../lib/translation-client";

export function bubbleTranslationRegions(regions: TextRegion[]) {
  // Current OCR uses "other" when it cannot classify text. Do not guess that
  // unknown regions are sound effects or discard their review metadata.
  return regions.filter(
    (region) => region.type !== "soundEffect" && region.text.trim(),
  );
}

export function useBubbleTranslations(
  regions: TextRegion[],
  enabled: boolean,
  attempt: number,
) {
  const [translations, setTranslations] = useState<Map<string, string>>(
    new Map(),
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setTranslations(new Map());
    setError(null);
    if (!enabled) return () => controller.abort();

    // One local inference at a time. Deduplicate repeated text within this run;
    // re-enabling goes through the provider-aware service cache so changing the
    // selected model never reuses a result from a different provider in the UI.
    const translate = async () => {
      const completed = new Map<string, string>();
      try {
        for (const region of regions) {
          if (controller.signal.aborted) return;
          const source = region.text.trim();
          if (!completed.has(source)) {
            const result = await requestTranslation(source, controller.signal);
            if (controller.signal.aborted) return;
            if (result.sourceText !== source || !result.translatedText.trim()) {
              throw new Error("Translation service returned an invalid result");
            }
            completed.set(source, result.translatedText);
          }
          setTranslations((previous) =>
            new Map(previous).set(region.id, completed.get(source)!),
          );
        }
      } catch (reason) {
        // Stop the queue on failure, including missing model/setup errors.
        if (!controller.signal.aborted)
          setError(String(reason).replace(/^Error: /, ""));
      }
    };
    void translate();
    return () => controller.abort();
  }, [regions, enabled, attempt]);

  return {
    translations,
    pending: enabled && !error && translations.size < regions.length,
    error,
  };
}
