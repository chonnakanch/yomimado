import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { ScanModeButton, type ScanMode } from "./ScanModeButton";
import { ToolbarIcon } from "./ToolbarIcon";
import "./toolbar.css";

export interface ToolbarState {
  revision: number;
  sessionId: number | null;
  phase:
    | "idle"
    | "selecting"
    | "capturing"
    | "recognizing"
    | "reviewing"
    | "ready"
    | "noText"
    | "error";
  message: string;
  canRescan: boolean;
  hasOverlay: boolean;
  overlayVisible: boolean;
  displayName: string;
  availableWidth: number;
  detectorModel: { required: boolean; installed: boolean };
}

const collapseKey = "yomimado.toolbar.collapsed.v1";

export function FloatingToolbar() {
  const [state, setState] = useState<ToolbarState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return window.localStorage.getItem(collapseKey) === "true";
    } catch {
      return false;
    }
  });
  const [menuOpen, setMenuOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const content = useRef<HTMLDivElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const busy = pending || state?.sessionId != null;
  const missingModel =
    state?.detectorModel.required && !state.detectorModel.installed;

  useEffect(() => {
    let mounted = true;
    let unlisten: UnlistenFn | undefined;
    const update = (next: ToolbarState) => {
      if (mounted)
        setState((previous) =>
          !previous || next.revision >= previous.revision ? next : previous,
        );
    };
    const refresh = () => {
      void invoke<ToolbarState>("get_toolbar_state")
        .then(update)
        .catch((e) => {
          if (mounted) setError(String(e));
        });
    };
    void listen<ToolbarState>("toolbar-state-changed", (event) =>
      update(event.payload),
    )
      .then((stop) => {
        if (!mounted) {
          stop();
          return;
        }
        unlisten = stop;
        refresh();
      })
      .catch((e) => {
        if (mounted) {
          setError(String(e));
          refresh();
        }
      });
    const blur = () => setMenuOpen(false);
    window.addEventListener("focus", refresh);
    window.addEventListener("blur", blur);
    return () => {
      mounted = false;
      unlisten?.();
      window.removeEventListener("focus", refresh);
      window.removeEventListener("blur", blur);
    };
  }, []);

  useEffect(() => {
    const element = content.current;
    if (!element) return;
    let lastSize = "";
    const resize = () => {
      const { width, height } = element.getBoundingClientRect();
      if (!width || !height) return;
      const logicalWidth = Math.ceil(width);
      const logicalHeight = Math.ceil(height);
      const size = `${logicalWidth}:${logicalHeight}`;
      if (size === lastSize) return;
      lastSize = size;
      void invoke("resize_toolbar", { logicalWidth, logicalHeight }).catch(
        (e) => setError(String(e)),
      );
    };
    const observer =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(resize);
    observer?.observe(element);
    resize();
    return () => observer?.disconnect();
  }, [
    collapsed,
    menuOpen,
    error,
    state?.message,
    state?.sessionId,
    missingModel,
  ]);

  useEffect(() => {
    if (menuOpen)
      menu.current?.querySelector<HTMLButtonElement>("button")?.focus();
  }, [menuOpen]);

  const run = async (command: string, args?: Record<string, unknown>) => {
    setError(null);
    setPending(true);
    setMenuOpen(false);
    try {
      await invoke(command, args);
      const snapshot = await invoke<ToolbarState>("get_toolbar_state");
      setState((previous) =>
        !previous || snapshot.revision >= previous.revision
          ? snapshot
          : previous,
      );
    } catch (e) {
      setError(String(e).replace(/^Error: /, ""));
    } finally {
      setPending(false);
    }
  };

  const collapse = () => {
    const next = !collapsed;
    setCollapsed(next);
    setMenuOpen(false);
    try {
      window.localStorage.setItem(collapseKey, String(next));
    } catch {
      setError(
        "Toolbar size preference could not be saved. You can still use it.",
      );
    }
  };

  const closeMenu = () => {
    setMenuOpen(false);
    menuButton.current?.focus();
  };
  const navigateMenu = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closeMenu();
      return;
    }
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const buttons = Array.from(
      menu.current?.querySelectorAll<HTMLButtonElement>(
        "button:not(:disabled)",
      ) ?? [],
    );
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
  const scan = (mode: ScanMode) => {
    void run("start_toolbar_scan", { mode });
  };
  const status =
    error ??
    (missingModel
      ? "Install the detector model in Scan & OCR to start reading."
      : (state?.message ?? "Connecting to YomiMado…"));
  const showStatus =
    !!error ||
    missingModel ||
    busy ||
    state?.phase === "error" ||
    state?.phase === "noText" ||
    state?.message.startsWith("Overlay restored") ||
    state?.message.startsWith("OCR overlays hidden");

  return (
    <div
      className={`floating-toolbar${collapsed ? " collapsed" : ""}`}
      ref={content}
      style={{
        width: collapsed ? 112 : Math.min(520, state?.availableWidth ?? 520),
      }}
    >
      <div
        className="floating-toolbar-row"
        aria-label="YomiMado reading toolbar"
      >
        <button
          className="utility-button utility-icon-button toolbar-drag"
          aria-label="Move toolbar"
          title="Drag to move. Arrow keys move the focused handle."
          onPointerDown={(event) => {
            if (event.button === 0)
              void invoke("drag_toolbar").catch((e) => setError(String(e)));
          }}
          onKeyDown={(event) => {
            const direction = {
              ArrowLeft: [-8, 0],
              ArrowRight: [8, 0],
              ArrowUp: [0, -8],
              ArrowDown: [0, 8],
            }[event.key];
            if (!direction) return;
            event.preventDefault();
            void invoke("move_toolbar", {
              dx: direction[0],
              dy: direction[1],
            }).catch((e) => setError(String(e)));
          }}
        >
          ⠿
        </button>
        {!collapsed && (
          <>
            <span className="toolbar-brand" aria-label="YomiMado">
              <ToolbarIcon name="book" />
            </span>
            <ScanModeButton
              mode="selectedArea"
              disabled={!state || busy || !!missingModel}
              displayName={state?.displayName ?? "current monitor"}
              onScan={scan}
            />
            <ScanModeButton
              mode="wholeScreen"
              disabled={!state || busy || !!missingModel}
              displayName={state?.displayName ?? "current monitor"}
              onScan={scan}
            />
          </>
        )}
        <button
          className="utility-button utility-icon-button"
          aria-label="Rescan"
          title={
            state?.canRescan
              ? "Rescan the last successful area or screen"
              : "Scan an area or screen first"
          }
          disabled={!state?.canRescan || busy || !!missingModel}
          onClick={() => void run("rescan")}
        >
          <ToolbarIcon name="rescan" />
        </button>
        {!collapsed && (
          <>
            <button
              className="utility-button utility-icon-button"
              aria-label={
                state?.overlayVisible
                  ? "Hide OCR overlays"
                  : "Show OCR overlays"
              }
              aria-pressed={state?.overlayVisible ?? false}
              disabled={!state?.hasOverlay || busy}
              title="Show or hide the last OCR result without scanning"
              onClick={() =>
                void run("set_overlay_visibility", {
                  visible: !state?.overlayVisible,
                })
              }
            >
              <ToolbarIcon
                name={state?.overlayVisible ? "visible" : "hidden"}
              />
            </button>
            <button
              className="utility-button utility-icon-button"
              aria-label="More actions"
              aria-expanded={menuOpen}
              aria-controls="toolbar-menu"
              ref={menuButton}
              onClick={() => setMenuOpen((previous) => !previous)}
            >
              <ToolbarIcon name="menu" />
            </button>
          </>
        )}
        <button
          className="utility-button utility-icon-button"
          aria-label={collapsed ? "Expand toolbar" : "Collapse toolbar"}
          title={collapsed ? "Expand toolbar" : "Collapse toolbar"}
          onClick={collapse}
        >
          <ToolbarIcon name={collapsed ? "expand" : "collapse"} />
        </button>
      </div>
      {!collapsed && (
        <div
          className={showStatus ? "toolbar-status" : "visually-hidden"}
          role={error || state?.phase === "error" ? "alert" : "status"}
        >
          <span>{status}</span>
          {missingModel && (
            <button
              className="toolbar-status-action"
              disabled={busy}
              onClick={() =>
                void run("show_secondary_window", { view: "settings" })
              }
            >
              Scan & OCR
            </button>
          )}
          {state?.sessionId != null && (
            <button
              className="toolbar-status-action"
              onClick={() =>
                void run("cancel_capture_selector", {
                  sessionId: state.sessionId,
                })
              }
            >
              Cancel scan
            </button>
          )}
        </div>
      )}
      {menuOpen && (
        <div
          className="toolbar-menu"
          id="toolbar-menu"
          aria-label="More actions"
          ref={menu}
          onKeyDown={navigateMenu}
        >
          <button
            disabled={busy}
            onClick={() => void run("show_secondary_window", { view: "words" })}
          >
            Saved words
          </button>
          <button
            disabled={busy}
            onClick={() =>
              void run("show_secondary_window", { view: "sentences" })
            }
          >
            Saved sentences
          </button>
          <button
            disabled={busy}
            onClick={() =>
              void run("show_secondary_window", { view: "settings" })
            }
          >
            Settings · Scan & OCR
          </button>
          <button
            disabled={busy}
            onClick={() =>
              void run("show_secondary_window", { view: "sources" })
            }
          >
            Sources & licenses
          </button>
          <button
            onClick={() =>
              void invoke("quit_app").catch((e) => setError(String(e)))
            }
          >
            Quit YomiMado
          </button>
        </div>
      )}
    </div>
  );
}
