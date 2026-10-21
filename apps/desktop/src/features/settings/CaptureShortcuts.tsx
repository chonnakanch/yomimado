import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

type Action = "selectedArea" | "wholeScreen";
type Bindings = Record<Action, string>;
interface Snapshot {
  bindings: Bindings;
  defaults: Bindings;
  available: [boolean, boolean];
  warnings: string[];
}
const actions: { id: Action; label: string }[] = [
  { id: "selectedArea", label: "Selected Area" },
  { id: "wholeScreen", label: "Whole Screen" },
];

function snapshot(value: Snapshot): Snapshot {
  if (
    !value ||
    !actions.every(
      ({ id }) =>
        typeof value.bindings?.[id] === "string" &&
        typeof value.defaults?.[id] === "string",
    ) ||
    !Array.isArray(value.available) ||
    value.available.length !== 2 ||
    !value.available.every((item) => typeof item === "boolean") ||
    !Array.isArray(value.warnings) ||
    !value.warnings.every((item) => typeof item === "string")
  )
    throw new Error("Shortcut settings returned an invalid response.");
  return value;
}

function display(shortcut: string): string {
  const mac = navigator.userAgent.includes("Mac");
  const names: Record<string, string> = {
    control: "Ctrl",
    shift: "Shift",
    alt: mac ? "Option" : "Alt",
    super: mac ? "Cmd" : "Windows",
  };
  return shortcut
    .split("+")
    .map((key) => names[key.toLowerCase()] ?? key.replace(/^(Key|Digit)/, ""))
    .join(" + ");
}

export function CaptureShortcuts({ active }: { active: boolean }) {
  const [data, setData] = useState<Snapshot | null>(null);
  const [ready, setReady] = useState(false);
  const [recording, setRecording] = useState<Action | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const current = useRef(data);
  const mounted = useRef(true);
  const visible = useRef(active);
  visible.current = active;
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const recorder = useRef<Action | null>(null);
  const pending = useRef(false);
  const candidate = useRef<{ code: string; shortcut: string } | null>(null);
  const generation = useRef(0);
  const buttons = useRef<Partial<Record<Action, HTMLButtonElement | null>>>({});
  const choose = useRef<(shortcut: string) => void>(() => {});
  const restoreFocus = useRef<Action | null>(null);
  useEffect(() => {
    if (!busy && active && restoreFocus.current) {
      buttons.current[restoreFocus.current]?.focus();
      restoreFocus.current = null;
    }
  }, [busy, recording, active]);
  current.current = data;

  const stop = () => {
    if (!recorder.current) return;
    recorder.current = null;
    candidate.current = null;
    if (mounted.current) setRecording(null);
    void invoke("record_capture_shortcut", { recording: false }).catch(() => {
      if (mounted.current)
        setError(
          "Could not stop the recorder. Refocus or close Settings to cancel it.",
        );
    });
  };

  const save = async (bindings: Bindings, success: string) => {
    if (pending.current) return;
    pending.current = true;
    generation.current++;
    const action = recorder.current;
    stop();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = snapshot(
        await invoke<Snapshot>("set_capture_shortcuts", { bindings }),
      );
      if (mounted.current) {
        setData(updated);
        setMessage(success);
      }
    } catch (reason) {
      if (mounted.current) setError(String(reason).replace(/^Error: /, ""));
    } finally {
      pending.current = false;
      if (mounted.current) {
        setBusy(false);
        if (action && visible.current) restoreFocus.current = action;
      }
    }
  };
  choose.current = (shortcut) => {
    const action = recorder.current;
    if (!action || !current.current) return;
    void save(
      { ...current.current.bindings, [action]: shortcut },
      "Shortcut saved and active. No restart needed.",
    );
  };

  useEffect(() => {
    if (!active) return;
    let disposed = false;
    let unlisten: (() => void) | undefined;
    const id = ++generation.current;
    setReady(false);
    setBusy(pending.current);
    setError("");
    void listen<string>("capture-shortcut-recorded", ({ payload }) => {
      if (!disposed) choose.current(payload);
    })
      .then((cleanup) => {
        if (disposed) cleanup();
        else {
          unlisten = cleanup;
          setReady(true);
        }
      })
      .catch(() => {
        if (!disposed)
          setError(
            "Could not start shortcut recording. Reopen Settings to retry.",
          );
      });
    void invoke<Snapshot>("capture_shortcuts")
      .then(snapshot)
      .then((value) => {
        if (!disposed && generation.current === id) setData(value);
      })
      .catch((reason) => {
        if (!disposed)
          setError(
            `Could not load shortcuts: ${String(reason).replace(/^Error: /, "")}`,
          );
      });
    const blur = () => {
      if (recorder.current || pending.current) generation.current++;
      stop();
    };
    const keydown = (event: KeyboardEvent) => {
      if (!recorder.current) return;
      if (
        event.key === "Tab" &&
        !event.ctrlKey &&
        !event.metaKey &&
        !event.altKey
      ) {
        stop();
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      if (event.key === "Escape") {
        stop();
        return;
      }
      if (event.repeat || /^(Control|Shift|Alt|Meta)$/.test(event.key)) return;
      if (
        event.isComposing ||
        event.getModifierState("AltGraph") ||
        !(event.ctrlKey || event.metaKey || event.altKey) ||
        !/^(Key[A-Z]|Digit[0-9]|F([1-9]|1[0-9]|2[0-4]))$/.test(event.code)
      ) {
        setError(
          "Use Ctrl, Command/Windows or Alt with a letter, number or F1–F24. Shift is optional.",
        );
        return;
      }
      candidate.current = {
        code: event.code,
        shortcut: [
          event.ctrlKey && "Control",
          event.altKey && "Alt",
          event.shiftKey && "Shift",
          event.metaKey && "Super",
          event.code,
        ]
          .filter(Boolean)
          .join("+"),
      };
      setMessage("Release the key to save your shortcut.");
    };
    const keyup = (event: KeyboardEvent) => {
      if (recorder.current && candidate.current?.code === event.code) {
        event.preventDefault();
        event.stopPropagation();
        choose.current(candidate.current.shortcut);
      }
    };
    window.addEventListener("blur", blur);
    window.addEventListener("keydown", keydown, true);
    window.addEventListener("keyup", keyup, true);
    return () => {
      disposed = true;
      generation.current++;
      stop();
      unlisten?.();
      window.removeEventListener("blur", blur);
      window.removeEventListener("keydown", keydown, true);
      window.removeEventListener("keyup", keyup, true);
    };
  }, [active]);

  const begin = async (action: Action) => {
    if (pending.current || !data || !ready) return;
    if (recorder.current === action) {
      stop();
      return;
    }
    pending.current = true;
    setBusy(true);
    setError("");
    setMessage("");
    const id = generation.current;
    try {
      await invoke("record_capture_shortcut", { recording: true });
      if (generation.current !== id || !document.hasFocus()) {
        await invoke("record_capture_shortcut", { recording: false });
        return;
      }
      recorder.current = action;
      setRecording(action);
      restoreFocus.current = action;
    } catch (reason) {
      if (generation.current === id)
        setError(String(reason).replace(/^Error: /, ""));
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  };

  return (
    <div className="settings-card">
      <div className="settings-card-heading">
        <h2>Scan shortcuts</h2>
        <button
          className="utility-button"
          disabled={!data || busy || Boolean(recording)}
          onClick={() =>
            data &&
            void save(data.defaults, "Default shortcuts restored and active.")
          }
        >
          Restore defaults
        </button>
      </div>
      <dl className="settings-shortcuts">
        {actions.map(({ id, label }, index) => (
          <div key={id}>
            <dt>{label}</dt>
            <dd>
              <kbd>{data ? display(data.bindings[id]) : "Loading…"}</kbd>
              {data && !data.available[index] && <span>Unavailable</span>}
              <button
                ref={(button) => {
                  buttons.current[id] = button;
                }}
                className="utility-button"
                aria-label={`Change ${label} shortcut`}
                aria-pressed={recording === id}
                aria-describedby="shortcut-recording-help"
                disabled={
                  !data ||
                  !ready ||
                  busy ||
                  Boolean(recording && recording !== id)
                }
                onClick={() => void begin(id)}
              >
                {recording === id ? "Cancel recording" : "Change"}
              </button>
            </dd>
          </div>
        ))}
      </dl>
      <p id="shortcut-recording-help" role="status">
        {busy
          ? "Updating shortcuts…"
          : recording
            ? "Press your new shortcut. Escape cancels; Tab moves on without saving."
            : "Choose Change, then press a key combination. Changes save automatically on this computer."}
      </p>
      {error && (
        <p className="settings-error" role="alert">
          {error}
        </p>
      )}
      {data?.warnings.map((warning, index) => (
        <p className="settings-error" key={index}>
          {warning}
        </p>
      ))}
      <p className="settings-success" role="status">
        {message}
      </p>
      <p>
        Shortcuts use the monitor under the pointer. Toolbar buttons use the
        toolbar's monitor. Rescan takes a fresh capture of your last successful
        area or screen.
      </p>
      <p className="settings-note">
        Whole Screen finds manga pages on the target monitor before OCR. If
        detection is uncertain, it uses a saved manga area or asks you to draw
        one. Selected Area scans exactly what you drag. Rescan repeats the last
        successful area; use Whole Screen again if the page has moved.
      </p>
    </div>
  );
}
