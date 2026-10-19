import { useSyncExternalStore } from "react";

export const jlptPreferenceKey = "yomimado.jlpt-tags.visible.v1";
const changed = "yomimado-jlpt-tags-changed";

function visible(): boolean {
  try {
    return window.localStorage.getItem(jlptPreferenceKey) !== "false";
  } catch {
    return true;
  }
}

function subscribe(update: () => void) {
  const onStorage = (event: StorageEvent) => {
    if (event.key === jlptPreferenceKey || event.key === null) update();
  };
  window.addEventListener("storage", onStorage);
  window.addEventListener(changed, update);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener(changed, update);
  };
}

export function useJlptVisible(): boolean {
  return useSyncExternalStore(subscribe, visible);
}

export function setJlptVisible(next: boolean): void {
  window.localStorage.setItem(jlptPreferenceKey, String(next));
  window.dispatchEvent(new Event(changed));
}
