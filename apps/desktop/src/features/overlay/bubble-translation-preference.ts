import { useSyncExternalStore } from "react";

export const bubbleTranslationPreferenceKey =
  "yomimado.bubble-translation.enabled.v1";
const changed = "yomimado-bubble-translation-changed";

function enabled(): boolean {
  try {
    return (
      window.localStorage.getItem(bubbleTranslationPreferenceKey) === "true"
    );
  } catch {
    return false;
  }
}

function subscribe(update: () => void) {
  const onStorage = (event: StorageEvent) => {
    if (event.key === bubbleTranslationPreferenceKey || event.key === null)
      update();
  };
  window.addEventListener("storage", onStorage);
  window.addEventListener(changed, update);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener(changed, update);
  };
}

export function useBubbleTranslationEnabled(): boolean {
  return useSyncExternalStore(subscribe, enabled);
}

export function setBubbleTranslationEnabled(next: boolean): void {
  window.localStorage.setItem(bubbleTranslationPreferenceKey, String(next));
  window.dispatchEvent(new Event(changed));
}
