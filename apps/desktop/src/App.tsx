import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";

export function App() {
  const [message, setMessage] = useState("Ready to capture a screen region.");

  const startCapture = async () => {
    try {
      await invoke("show_capture_selector");
      setMessage("Drag over Japanese text in the capture window.");
    } catch (error) {
      setMessage(`Unable to open capture selection: ${String(error)}`);
    }
  };

  return (
    <main className="main-window">
      <h1>
        YomiMado <span>読み窓</span>
      </h1>
      <p>Read beyond the page.</p>
      <button onClick={startCapture}>Select screen region</button>
      <p className="status">{message}</p>
      <p className="hint">Shortcut: Cmd/Ctrl + Shift + O</p>
    </main>
  );
}
