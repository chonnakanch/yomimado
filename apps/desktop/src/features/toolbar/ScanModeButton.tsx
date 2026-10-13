import { ToolbarIcon } from "./ToolbarIcon";

export type ScanMode = "selectedArea" | "wholeScreen";

export function ScanModeButton({
  mode,
  disabled,
  displayName,
  onScan,
}: {
  mode: ScanMode;
  disabled: boolean;
  displayName: string;
  onScan: (mode: ScanMode) => void;
}) {
  return (
    <button
      type="button"
      className={`utility-button${mode === "selectedArea" ? " utility-button-primary" : ""}`}
      disabled={disabled}
      title={`Scan ${displayName}`}
      onClick={() => onScan(mode)}
    >
      <ToolbarIcon name={mode === "selectedArea" ? "area" : "screen"} />
      {mode === "selectedArea" ? "Selected Area" : "Whole Screen"}
    </button>
  );
}
