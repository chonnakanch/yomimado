import { useEffect, useRef, useState } from "react";
import { invoke, isTauri } from "@tauri-apps/api/core";
import { postServiceJson, requestService } from "../../lib/service-client";
import { TranslationDownload } from "./TranslationDownload";

type Provider = "builtin" | "imported" | "ollama";
interface Settings {
  provider: Provider;
  importedModel: string | null;
  ollamaModel: string;
  backend: "torch" | "onnx";
}
interface Download {
  state: "idle" | "downloading" | "ready" | "error";
  model: string;
  message: string;
  completed: number;
  total: number;
}
interface OllamaStatus {
  models: { name: string; digest: string }[];
  error: string | null;
  download: Download;
}

function parseSettings(value: unknown): Settings {
  if (
    !value ||
    typeof value !== "object" ||
    !("provider" in value) ||
    !["builtin", "imported", "ollama"].includes(String(value.provider)) ||
    !("backend" in value) ||
    !["torch", "onnx"].includes(String(value.backend)) ||
    !("ollamaModel" in value) ||
    typeof value.ollamaModel !== "string" ||
    !("importedModel" in value) ||
    (value.importedModel !== null && typeof value.importedModel !== "string")
  )
    throw new Error("Translation settings returned an invalid response");
  return value as Settings;
}

function parseOllama(value: unknown): OllamaStatus {
  if (
    !value ||
    typeof value !== "object" ||
    !("models" in value) ||
    !Array.isArray(value.models) ||
    !value.models.every(
      (item) =>
        item &&
        typeof item.name === "string" &&
        typeof item.digest === "string",
    ) ||
    !("error" in value) ||
    (value.error !== null && typeof value.error !== "string") ||
    !("download" in value) ||
    !value.download ||
    typeof value.download !== "object"
  )
    throw new Error("Ollama returned an invalid status");
  const job = value.download;
  if (
    !("state" in job) ||
    !["idle", "downloading", "ready", "error"].includes(String(job.state)) ||
    !("message" in job) ||
    typeof job.message !== "string" ||
    !("model" in job) ||
    typeof job.model !== "string" ||
    !("completed" in job) ||
    !Number.isSafeInteger(job.completed) ||
    Number(job.completed) < 0 ||
    !("total" in job) ||
    !Number.isSafeInteger(job.total) ||
    Number(job.total) < Number(job.completed)
  )
    throw new Error("Ollama returned invalid download progress");
  return value as OllamaStatus;
}

const endpoint = "/api/v1/translation-settings";
const message = (reason: unknown) =>
  reason instanceof Error ? reason.message : String(reason);

export function TranslationModels({ active }: { active: boolean }) {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [source, setSource] = useState<Provider>("builtin");
  const [folder, setFolder] = useState("");
  const [model, setModel] = useState("");
  const [ollama, setOllama] = useState<OllamaStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [ollamaRefresh, setOllamaRefresh] = useState(0);
  const pending = useRef(false);
  const generation = useRef(0);

  useEffect(() => {
    if (!active) return;
    const id = ++generation.current;
    void requestService(endpoint, "Translation settings")
      .then((response) => response.json())
      .then(parseSettings)
      .then((value) => {
        if (id !== generation.current) return;
        setSettings(value);
        setSource(value.provider);
        setModel(value.ollamaModel);
        setError(null);
      })
      .catch((reason) => {
        if (id === generation.current) setError(message(reason));
      });
    return () => {
      generation.current++;
    };
  }, [active, refresh]);

  useEffect(() => {
    if (!active || source !== "ollama") return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const check = async () => {
      try {
        const response = await requestService(
          endpoint + "/ollama",
          "Ollama setup",
        );
        const value = parseOllama(await response.json());
        if (cancelled) return;
        setOllama(value);
        if (value.download.state === "downloading")
          timer = setTimeout(check, 1000);
      } catch (reason) {
        if (!cancelled) setError(message(reason));
      }
    };
    void check();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [active, source, ollamaRefresh]);

  const run = async (operation: () => Promise<void>) => {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError(null);
    // A delayed status read must never overwrite a completed user selection.
    generation.current++;
    try {
      await operation();
    } catch (reason) {
      setError(message(reason));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  };
  const select = (provider: Provider) =>
    run(async () => {
      setSettings(
        parseSettings(
          await postServiceJson(endpoint, "Translation settings", {
            provider,
            model,
          }),
        ),
      );
    });
  const importFolder = () =>
    run(async () => {
      setSettings(
        parseSettings(
          await postServiceJson(endpoint + "/import", "Model import", {
            folder,
          }),
        ),
      );
    });
  const browse = () =>
    run(async () => {
      if (!isTauri())
        throw new Error(
          "Enter the model folder’s full path in this browser preview. The desktop app provides a folder picker.",
        );
      const selected = await invoke<string | null>(
        "choose_translation_model_folder",
      );
      if (selected) setFolder(selected);
    });
  const downloading = ollama?.download.state === "downloading";

  return (
    <>
      <div className="settings-card">
        <h2>Translation model</h2>
        <p>
          Choose how to translate Japanese into English. Models stay on this
          computer; translation runs only when you request it.
        </p>
        {settings && (
          <p role="status">
            Using:{" "}
            {settings.provider === "builtin"
              ? "Built-in Marian model"
              : settings.provider === "imported"
                ? settings.importedModel
                : `Ollama · ${settings.ollamaModel}`}
            .
          </p>
        )}
        <label className="settings-model-field">
          Model source
          <select
            value={source}
            disabled={busy || !settings}
            onChange={(event) => {
              setSource(event.target.value as Provider);
              setError(null);
            }}
          >
            <option value="builtin">Built-in model</option>
            <option value="imported">Import local model</option>
            <option value="ollama">Ollama</option>
          </select>
        </label>
        {source === "builtin" && settings?.provider !== "builtin" && (
          <button
            className="utility-button"
            disabled={busy || !settings}
            onClick={() => void select("builtin")}
          >
            Use built-in model
          </button>
        )}
        {source === "imported" && (
          <>
            <p>
              {settings?.backend === "onnx"
                ? "Choose a Japanese-to-English Marian export folder containing model/ and onnx/ in YomiMado’s ONNX format."
                : "Choose a downloaded Japanese-to-English Marian model folder containing its tokenizer and Torch or Safetensors weights."}{" "}
              For GGUF and other model families, use Ollama.
            </p>
            <label className="settings-model-field">
              Model folder
              <input
                value={folder}
                disabled={busy}
                onChange={(event) => setFolder(event.target.value)}
                placeholder="Full path to model folder"
              />
            </label>
            <div className="settings-model-actions">
              <button
                className="utility-button"
                disabled={busy}
                onClick={() => void browse()}
              >
                Browse folders…
              </button>
              <button
                className="utility-button"
                disabled={busy || !folder.trim()}
                onClick={() => void importFolder()}
              >
                {busy ? "Checking model…" : "Import and use model"}
              </button>
              {settings?.importedModel && settings.provider !== "imported" && (
                <button
                  className="utility-button"
                  disabled={busy}
                  onClick={() => void select("imported")}
                >
                  Use {settings.importedModel}
                </button>
              )}
            </div>
            <p className="settings-note">
              YomiMado copies and checks the model before selecting it. Your
              previous model stays available if import fails. Use models whose
              terms allow your intended use.
            </p>
          </>
        )}
        {source === "ollama" && (
          <>
            <p>
              Install and open{" "}
              <a
                href="https://ollama.com/download"
                target="_blank"
                rel="noreferrer"
              >
                Ollama
              </a>{" "}
              first. Choose a local text model that understands Japanese. Model
              size, speed and translation quality depend on your choice. Cloud
              models are excluded.
            </p>
            <button
              className="utility-button"
              disabled={busy}
              onClick={() => {
                setError(null);
                setOllamaRefresh((value) => value + 1);
              }}
            >
              Refresh Ollama models
            </button>
            {ollama?.error && (
              <p className="settings-error" role="alert">
                {ollama.error}
              </p>
            )}
            <label className="settings-model-field">
              Installed Ollama model
              <select
                value={
                  ollama?.models.some((item) => item.name === model)
                    ? model
                    : ""
                }
                disabled={busy || !ollama?.models.length}
                onChange={(event) => setModel(event.target.value)}
              >
                <option value="">Choose a model</option>
                {ollama?.models.map((item) => (
                  <option key={item.name} value={item.name}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="settings-model-field">
              Ollama model name
              <input
                value={model}
                disabled={busy || downloading}
                onChange={(event) => setModel(event.target.value)}
                placeholder="model:tag"
              />
            </label>
            <div className="settings-model-actions">
              <button
                className="utility-button"
                disabled={
                  busy || downloading || !model.trim() || !!ollama?.error
                }
                onClick={() =>
                  void run(async () => {
                    const job = parseOllama({
                      models: [],
                      error: null,
                      download: await postServiceJson(
                        endpoint + "/ollama/pull",
                        "Ollama download",
                        { model },
                      ),
                    }).download;
                    setModel(job.model);
                    setOllamaRefresh((value) => value + 1);
                  })
                }
              >
                {downloading ? "Downloading…" : "Download in Ollama"}
              </button>
              <button
                className="utility-button"
                disabled={
                  busy || !ollama?.models.some((item) => item.name === model)
                }
                onClick={() => void select("ollama")}
              >
                Use this model
              </button>
            </div>
            {ollama?.download.state !== "idle" && ollama?.download && (
              <>
                <p
                  role={ollama.download.state === "error" ? "alert" : "status"}
                >
                  {ollama.download.model}: {ollama.download.message}
                </p>
                {downloading && ollama.download.total > 0 && (
                  <progress
                    aria-label="Ollama model download"
                    max={ollama.download.total}
                    value={ollama.download.completed}
                  />
                )}
              </>
            )}
            <p className="settings-note">
              Downloading may use several GB. Downloads require your click and
              stay managed by Ollama. Switching models does not delete them.
            </p>
          </>
        )}
        {error && (
          <>
            <p className="settings-error" role="alert">
              {error}
            </p>
            <button
              className="utility-button"
              disabled={busy}
              onClick={() => setRefresh((value) => value + 1)}
            >
              Try again
            </button>
          </>
        )}
      </div>
      {source === "builtin" && (
        <TranslationDownload active={active && source === "builtin"} />
      )}
    </>
  );
}
