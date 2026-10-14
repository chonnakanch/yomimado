import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { invoke } from "@tauri-apps/api/core";
import { type ToolbarState } from "./FloatingToolbar";
import "./toolbar.css";

const items = [
  { label: "Saved", view: "saved" },
  { label: "Settings", view: "settings" },
  { label: "Sources & licenses", view: "sources" },
  { label: "Quit YomiMado", view: null },
] as const;

export function ToolbarMenu() {
  const [requestId] = useState(() =>
    Number(new URLSearchParams(window.location.search).get("request")),
  );
  const content = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<ToolbarState | null>(null);
  const [error, setError] = useState<string | null>(null);
  // This webview cannot inherit the toolbar's input modality. Native window
  // focus otherwise makes WebKit draw a keyboard ring after a mouse opening.
  const [keyboardFocus, setKeyboardFocus] = useState(false);
  const [maxHeight, setMaxHeight] = useState(600);
  const focusFirst = () =>
    content.current
      ?.querySelector<HTMLButtonElement>("button:not(:disabled)")
      ?.focus();
  useEffect(() => {
    let mounted = true;
    void invoke<ToolbarState>("get_toolbar_state")
      .then((snapshot) => {
        if (mounted) setState(snapshot);
      })
      .catch((reason) => {
        if (mounted) setError(String(reason));
      });
    window.addEventListener("focus", focusFirst);
    return () => {
      mounted = false;
      window.removeEventListener("focus", focusFirst);
    };
  }, []);
  useEffect(focusFirst, [state]);
  useEffect(() => {
    let disposed = false;
    let lastSize = "";
    let queue = Promise.resolve();
    const resize = () => {
      const bounds = content.current?.getBoundingClientRect();
      if (!bounds?.width || !bounds.height) return;
      const logicalWidth = Math.ceil(bounds.width),
        logicalHeight = Math.ceil(bounds.height);
      const size = `${logicalWidth}:${logicalHeight}`;
      if (size === lastSize) return;
      lastSize = size;
      queue = queue.then(async () => {
        if (disposed) return;
        try {
          const available = await invoke<number | null>(
            "position_toolbar_menu",
            { logicalWidth, logicalHeight, requestId },
          );
          if (!disposed && typeof available === "number")
            setMaxHeight(Math.min(600, available));
        } catch (reason) {
          if (!disposed) setError(String(reason));
        }
      });
    };
    const observer =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(resize);
    if (content.current) observer?.observe(content.current);
    resize();
    return () => {
      disposed = true;
      observer?.disconnect();
    };
  }, []);
  const close = () =>
    void invoke("close_toolbar_menu", { restoreFocus: true }).catch((reason) =>
      setError(String(reason)),
    );
  const navigate = (event: KeyboardEvent) => {
    if (["Tab", "ArrowDown", "ArrowUp", "Home", "End"].includes(event.key))
      setKeyboardFocus(true);
    if (event.key === "Escape") {
      event.preventDefault();
      close();
      return;
    }
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const buttons = [
      ...(content.current?.querySelectorAll<HTMLButtonElement>(
        "button:not(:disabled)",
      ) ?? []),
    ];
    const current = buttons.indexOf(
      document.activeElement as HTMLButtonElement,
    );
    const next =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? buttons.length - 1
          : (current + (event.key === "ArrowDown" ? 1 : -1) + buttons.length) %
            buttons.length;
    buttons[next]?.focus();
  };
  const run = async (view: (typeof items)[number]["view"]) => {
    try {
      await invoke("close_toolbar_menu");
      await invoke(
        view ? "show_secondary_window" : "quit_app",
        view ? { view } : undefined,
      );
    } catch (reason) {
      setError(String(reason));
    }
  };
  return (
    <div
      className={`toolbar-menu toolbar-menu-popover${keyboardFocus ? " keyboard-navigation" : ""}`}
      role="menu"
      aria-label="More actions"
      ref={content}
      onKeyDown={navigate}
      onPointerDown={() => setKeyboardFocus(false)}
      onPointerMove={() => setKeyboardFocus(false)}
      style={{ maxHeight }}
    >
      {items.map(({ label, view }) => (
        <button
          role="menuitem"
          key={label}
          disabled={view !== null && (!state || state.sessionId !== null)}
          onClick={() => void run(view)}
        >
          {label}
        </button>
      ))}
      {error && (
        <p className="toolbar-menu-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
