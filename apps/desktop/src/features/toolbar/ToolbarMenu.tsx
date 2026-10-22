import {
  Fragment,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { invoke } from "@tauri-apps/api/core";
import { emitTo } from "@tauri-apps/api/event";
import { type ToolbarState } from "./FloatingToolbar";
import "./toolbar.css";

const items = [
  { label: "Read with keyboard", view: "regions" },
  { label: "Saved", view: "saved" },
  { label: "Settings", view: "settings" },
  { label: "Sources & licenses", view: "sources" },
  { label: "Hide Toolbar", view: "hideToolbar" },
  { label: "Quit YomiMado", view: null },
] as const;

export function ToolbarMenu() {
  const [requestId] = useState(() =>
    Number(new URLSearchParams(window.location.search).get("request")),
  );
  const content = useRef<HTMLDivElement>(null);
  const menuItems = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<ToolbarState | null>(null);
  const [loaded, setLoaded] = useState(false);
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
      })
      .finally(() => {
        if (mounted) setLoaded(true);
      });
    window.addEventListener("focus", focusFirst);
    return () => {
      mounted = false;
      window.removeEventListener("focus", focusFirst);
    };
  }, []);
  useEffect(focusFirst, [state]);
  useEffect(() => {
    // The native popover stays hidden until tray availability determines the
    // complete item list. Otherwise its first frame can omit the final action.
    if (!loaded) return;
    let disposed = false;
    let lastSize = "";
    let queue = Promise.resolve();
    const resize = () => {
      const menu = content.current;
      const bounds = menu?.getBoundingClientRect();
      const itemsBounds = menuItems.current?.getBoundingClientRect();
      if (!menu || !bounds?.width || !itemsBounds?.height) return;
      const style = getComputedStyle(menu);
      const borderHeight =
        (parseFloat(style.borderTopWidth) || 0) +
        (parseFloat(style.borderBottomWidth) || 0);
      // Measure intrinsic content, not the scroll viewport constrained by the
      // previous native response. This also isolates fractional-DPI resizes.
      const logicalWidth = Math.ceil(bounds.width),
        logicalHeight = Math.min(
          600,
          Math.ceil(itemsBounds.height + borderHeight),
        );
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
    if (menuItems.current) observer?.observe(menuItems.current);
    resize();
    return () => {
      disposed = true;
      observer?.disconnect();
    };
  }, [loaded, requestId]);
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
      if (view === "regions") await invoke("focus_ocr_regions");
      else if (view === "hideToolbar") await invoke("hide_toolbar");
      else
        await invoke(
          view ? "show_secondary_window" : "quit_app",
          view ? { view } : undefined,
        );
    } catch (reason) {
      const message = `More actions failed: ${String(reason).replace(/^Error: /, "")}`;
      setError(message);
      // The menu is already hidden when a destination fails. Keep the error
      // available through the toolbar's existing status control.
      await emitTo("toolbar", "toolbar-action-error", message).catch(
        (failure) =>
          console.error("YomiMado: could not report menu error", failure),
      );
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
      <div className="toolbar-menu-content" ref={menuItems} role="presentation">
        {items
          .filter(({ view }) => view !== "hideToolbar" || state?.trayAvailable)
          .map(({ label, view }) => (
            <Fragment key={label}>
              {(view === "hideToolbar" ||
                (view === null && !state?.trayAvailable)) && (
                <div role="separator" />
              )}
              <button
                role="menuitem"
                disabled={
                  view !== null &&
                  (!state ||
                    state.sessionId !== null ||
                    (view === "regions" &&
                      (!state.hasOverlay || !state.overlayVisible)))
                }
                onClick={() => void run(view)}
              >
                {label}
              </button>
            </Fragment>
          ))}
        {error && (
          <p className="toolbar-menu-error" role="alert">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
