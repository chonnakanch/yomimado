import { ToolbarIcon } from "./ToolbarIcon";
import { debugTooltip } from "../../lib/debug-mode";

export type ScanMode = "selectedArea" | "wholeScreen";

export function ScanModeButton({
  mode,
  selected,
  compact,
  loadingLabel,
  disabled,
  displayName,
  onScan,
  onCancel,
}: {
  mode: ScanMode;
  selected: boolean;
  compact: boolean;
  loadingLabel: string | null;
  disabled: boolean;
  displayName: string;
  onScan: (mode: ScanMode) => void;
  onCancel?: () => void;
}) {
  const label = mode === "selectedArea" ? "Selected Area" : "Whole Screen";
  const description = loadingLabel
    ? `${label}: ${loadingLabel}${onCancel ? " Click to cancel this scan." : ""}`
    : mode === "wholeScreen"
      ? `${label} · Find manga pages on ${displayName}; use a saved or drawn area if uncertain`
      : `${label} · Scan ${displayName}`;
  return (
    <button
      type="button"
      className={`utility-button toolbar-scan-button${selected ? " utility-button-primary" : ""}${compact ? " utility-icon-button" : ""}`}
      aria-label={onCancel ? "Cancel scan" : label}
      aria-description={description}
      aria-pressed={selected}
      aria-busy={!!loadingLabel}
      disabled={disabled}
      title={debugTooltip(description)}
      onClick={() => (onCancel ? onCancel() : onScan(mode))}
    >
      <ToolbarIcon
        name={
          loadingLabel ? "loading" : mode === "selectedArea" ? "area" : "screen"
        }
      />
      {!compact && <span>{loadingLabel ?? label}</span>}
    </button>
  );
}
