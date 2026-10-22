import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { CaptureShortcuts } from "./CaptureShortcuts";

interface DetectorModelStatus {
  required: boolean;
  installed: boolean;
}

export function ScanSettings({ active }: { active: boolean }) {
  const [model, setModel] = useState<DetectorModelStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const mounted = useRef(false);
  const request = useRef(0);
  const importing = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      request.current++;
    };
  }, []);

  const refresh = async () => {
    if (importing.current) return;
    const id = ++request.current;
    setLoading(true);
    setError(null);
    setMessage("");
    try {
      const updated = await invoke<DetectorModelStatus>(
        "detector_model_status",
      );
      if (mounted.current && request.current === id) setModel(updated);
    } catch (reason) {
      if (mounted.current && request.current === id)
        setError(
          `Unable to check detector model setup: ${String(reason).replace(/^Error: /, "")}`,
        );
    } finally {
      if (mounted.current && request.current === id) setLoading(false);
    }
  };
  useEffect(() => {
    if (active) void refresh();
    return () => {
      request.current++;
    };
  }, [active]);

  const install = async () => {
    if (importing.current) return;
    importing.current = true;
    request.current++;
    setLoading(false);
    setInstalling(true);
    setError(null);
    setMessage("");
    try {
      const updated = await invoke<DetectorModelStatus | null>(
        "install_detector_model",
      );
      if (mounted.current && updated) {
        setModel(updated);
        setMessage(
          "Detector model installed. Restart YomiMado if you replaced a model already in use.",
        );
      }
    } catch (reason) {
      if (mounted.current)
        setError(
          `Unable to install detector model: ${String(reason).replace(/^Error: /, "")}`,
        );
    } finally {
      importing.current = false;
      if (mounted.current) setInstalling(false);
    }
  };

  const openRelease = async () => {
    setError(null);
    try {
      await invoke("open_detector_release");
    } catch (reason) {
      if (mounted.current)
        setError(
          `Unable to open the detector release page: ${String(reason).replace(/^Error: /, "")}. Copy the link address and open it in your browser.`,
        );
    }
  };

  return (
    <>
      <div className="settings-card">
        <div className="settings-card-heading">
          <h2>Detector model</h2>
          <button
            className="utility-button"
            disabled={loading || installing}
            onClick={() => void refresh()}
          >
            Refresh status
          </button>
        </div>
        <p
          role="status"
          className={`settings-model-status${model?.required && model.installed ? " status-chip status-chip-success" : ""}`}
        >
          {loading
            ? "Checking detector model…"
            : !model
              ? "Detector status unavailable."
              : !model.required
                ? "Managed by the development OCR service."
                : model.installed
                  ? "Installed on this computer."
                  : "Detector model required before scanning."}
        </p>
        {model?.required && (
          <>
            <p>
              Download <code>comictextdetector.pt.onnx</code> from the{" "}
              <a
                href="https://github.com/zyddnys/manga-image-translator/releases/latest"
                target="_blank"
                rel="noreferrer"
                onClick={(event) => {
                  event.preventDefault();
                  void openRelease();
                }}
              >
                latest release page
              </a>
              , then select the file. YomiMado verifies its checksum and stores
              a private copy on this computer. Nothing is downloaded by the app.
            </p>
            <button
              className="utility-button utility-button-primary"
              disabled={loading || installing}
              onClick={() => void install()}
            >
              {installing
                ? "Checking model…"
                : model.installed
                  ? "Replace detector model"
                  : "Select detector model file"}
            </button>
            <p className="settings-note">
              Replacing a model already in use requires restarting YomiMado.
              Canceling the file picker keeps the current model.
            </p>
          </>
        )}
        {model && !model.required && (
          <p>
            Local models are configured in your development service. This status
            does not check whether that service is ready to recognize text.
          </p>
        )}
        {error && (
          <p role="alert" className="settings-error">
            {error}
          </p>
        )}
        <p role="status" className="settings-success">
          {message}
        </p>
      </div>
      <div className="settings-card">
        <h2>Capture access</h2>
        <p>
          On macOS, allow YomiMado in System Settings → Privacy &amp; Security →
          Screen &amp; System Audio Recording, then restart the app. For
          command-based development, macOS may use your terminal's permission.
        </p>
        <p>
          On Windows, keep the reader on an interactive desktop. Capture errors
          appear on the toolbar with retry guidance.
        </p>
        <p className="settings-note">
          Capture access is checked when you scan. Screenshots stay local.
        </p>
      </div>
      <CaptureShortcuts active={active} />
    </>
  );
}
