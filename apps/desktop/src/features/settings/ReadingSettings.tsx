export function ReadingSettings() {
  return (
    <div className="settings-card">
      <h2>Reading</h2>
      <h3>Read with keyboard</h3>
      <p>
        After scanning, choose More actions → Read with keyboard on the toolbar.
        Show the OCR overlays first if they are hidden.
      </p>
      <p>
        Arrow keys move between regions. Home and End select the first and last
        region. Enter or Space opens the selected region’s learning popup.
        Escape closes the popup and returns to that region; press Escape again
        to hide the overlays and return to the toolbar.
      </p>
      <p className="settings-note">
        Navigation follows detected regions. Estimated order on whole-screen
        scans may differ from manga panel order; you can still click any region.
      </p>
    </div>
  );
}
