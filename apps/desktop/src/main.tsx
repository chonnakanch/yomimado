import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { CaptureSelector } from "./features/capture/CaptureSelector";
import { OcrOverlay } from "./features/overlay/OcrOverlay";
import { TranslationPopup } from "./features/translation/TranslationPopup";
import { FloatingToolbar } from "./features/toolbar/FloatingToolbar";
import { ToolbarMenu } from "./features/toolbar/ToolbarMenu";
import "./styles.css";

const mode = new URLSearchParams(window.location.search).get("mode");
document.documentElement.dataset.mode = mode ?? "main";
const root = ReactDOM.createRoot(document.getElementById("root")!);

root.render(
  <React.StrictMode>
    {mode === "toolbar-menu" ? (
      <ToolbarMenu />
    ) : mode === "toolbar" ? (
      <FloatingToolbar />
    ) : mode === "capture" ? (
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
