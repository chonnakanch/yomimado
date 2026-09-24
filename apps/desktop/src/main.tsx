import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { CaptureSelector } from "./features/capture/CaptureSelector";
import { OcrOverlay } from "./features/overlay/OcrOverlay";
import { TranslationPopup } from "./features/translation/TranslationPopup";
import "./styles.css";

const mode = new URLSearchParams(window.location.search).get("mode");
document.documentElement.dataset.mode = mode ?? "main";
const root = ReactDOM.createRoot(document.getElementById("root")!);

root.render(
  <React.StrictMode>
    {mode === "capture" ? (
      <CaptureSelector />
    ) : mode === "overlay" ? (
      <OcrOverlay />
    ) : mode === "translation" ? (
      <TranslationPopup />
    ) : (
      <App />
    )}
  </React.StrictMode>,
);
