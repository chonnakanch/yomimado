export function captureDebugEnabled(): boolean {
  return import.meta.env.VITE_CAPTURE_DEBUG === "1";
}

export function debugTooltip(text: string | null): string | undefined {
  return captureDebugEnabled() ? (text ?? undefined) : undefined;
}
