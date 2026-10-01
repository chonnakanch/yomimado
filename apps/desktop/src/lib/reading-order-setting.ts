export const readingOrderSettingKey = "yomimado.reading-order.enabled.v1";

export function readReadingOrderEnabled(): boolean {
  try {
    return window.localStorage.getItem(readingOrderSettingKey) === "true";
  } catch {
    return false;
  }
}

export function saveReadingOrderEnabled(enabled: boolean): void {
  window.localStorage.setItem(readingOrderSettingKey, String(enabled));
}
