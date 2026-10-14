import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { ScanModeButton, type ScanMode } from "./ScanModeButton";
import { ToolbarIcon } from "./ToolbarIcon";
import "./toolbar.css";

export interface ToolbarState {
  revision: number;
  sessionId: number | null;
  scanMode: ScanMode;
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
const progressLabels: Partial<Record<ToolbarState["phase"], string>> = {
  selecting: "Selecting…",
  capturing: "Capturing…",
  recognizing: "Recognizing…",
  reviewing: "Reviewing…",
};

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
  const [pendingScanMode, setPendingScanMode] = useState<ScanMode | null>(null);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const statusButton = useRef<HTMLButtonElement>(null);
  const feedback = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const busy = pending || state?.sessionId != null;
  const compact = collapsed || (state?.availableWidth ?? 520) < 520;
  const scanBusy = pendingScanMode !== null || state?.sessionId != null;
  const scanMode =
    state?.sessionId != null
      ? (state.scanMode ?? "selectedArea")
      : (pendingScanMode ?? state?.scanMode ?? "selectedArea");
  const progress = scanBusy
    ? (progressLabels[state?.phase ?? "idle"] ?? "Scanning…")
    : null;
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
    const blur = () => {
      setMenuOpen(false);
      setFeedbackOpen(false);
    };
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
  }, [compact, menuOpen, feedbackOpen, error, state?.sessionId, missingModel]);

  useEffect(() => {
    if (menuOpen)
      menu.current
        ?.querySelector<HTMLButtonElement>("button:not(:disabled)")
        ?.focus();
  }, [menuOpen]);

  const run = async (
    command: string,
    args?: Record<string, unknown>,
    mode?: ScanMode,
  ) => {
    setError(null);
    setPending(true);
    setPendingScanMode(mode ?? null);
    setMenuOpen(false);
    setFeedbackOpen(false);
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
      setPendingScanMode(null);
    }
  };

  const collapse = () => {
    const next = !collapsed;
    setCollapsed(next);
    setMenuOpen(false);
    setFeedbackOpen(false);
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
    void run("start_toolbar_scan", { mode }, mode);
  };
  const status =
    error ??
    (missingModel
      ? "Install the detector model in Scan & OCR to start reading."
      : (state?.message ?? "Connecting to YomiMado…"));
  const attention =
    !!error ||
    !!missingModel ||
    state?.phase === "error" ||
    state?.phase === "noText";
  useEffect(() => {
    if (!attention) setFeedbackOpen(false);
  }, [attention]);
  useEffect(() => {
    if (feedbackOpen)
      (
        feedback.current?.querySelector<HTMLButtonElement>(
          "button:not(:disabled)",
        ) ?? feedback.current
      )?.focus();
  }, [feedbackOpen]);
  const cancelScan =
    state?.sessionId != null
      ? () =>
          void run("cancel_capture_selector", { sessionId: state.sessionId })
      : undefined;

  return (
    <div
      className={`floating-toolbar${collapsed ? " collapsed" : ""}${compact ? " compact" : ""}`}
      ref={content}
      style={{
        width: Math.min(compact ? 224 : 520, state?.availableWidth ?? 520),
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
        {!compact && (
          <span className="toolbar-brand" aria-label="YomiMado">
            <ToolbarIcon name="book" />
          </span>
        )}
        {(["selectedArea", "wholeScreen"] as const).map((mode) => {
          const onCancel =
            scanBusy && mode === scanMode ? cancelScan : undefined;
          return (
            <ScanModeButton
              key={mode}
              mode={mode}
              selected={mode === scanMode}
              compact={compact}
              loadingLabel={mode === scanMode ? progress : null}
              disabled={!state || ((busy || !!missingModel) && !onCancel)}
              displayName={state?.displayName ?? "current monitor"}
              onScan={scan}
              onCancel={onCancel}
            />
          );
        })}
        <button
          className="utility-button utility-icon-button"
          aria-label="Rescan"
          title={
            state?.canRescan
              ? "Rescan the last successful area or screen"
              : "Scan an area or screen first"
          }
          disabled={!state?.canRescan || busy || !!missingModel}
          onClick={() =>
            void run("rescan", undefined, state?.scanMode ?? "selectedArea")
          }
        >
          <ToolbarIcon name="rescan" />
        </button>
        <button
          className={`utility-button utility-icon-button toolbar-overlay-status${state?.overlayVisible ? " is-visible" : ""}${attention ? " needs-attention" : ""}`}
          aria-label={
            attention
              ? "Scan status"
              : state?.overlayVisible
                ? "Hide OCR overlays"
                : "Show OCR overlays"
          }
          aria-pressed={
            attention ? undefined : (state?.overlayVisible ?? false)
          }
          aria-expanded={attention ? feedbackOpen : undefined}
          aria-controls={attention ? "toolbar-feedback" : undefined}
          disabled={attention ? busy : !state?.hasOverlay || busy}
          ref={statusButton}
          title={
            attention
              ? `${status} · Click for details`
              : !state?.hasOverlay
                ? "No OCR result yet. Scan Japanese text first."
                : state.overlayVisible
                  ? "OCR overlays shown · Click to hide"
                  : "OCR overlays hidden · Click to show"
          }
          onClick={() => {
            if (attention) {
              setMenuOpen(false);
              setFeedbackOpen((previous) => !previous);
            } else {
              void run("set_overlay_visibility", {
                visible: !state?.overlayVisible,
              });
            }
          }}
        >
          <ToolbarIcon
            name={
              attention
                ? "warning"
                : state?.overlayVisible
                  ? "visible"
                  : "hidden"
            }
          />
        </button>
        {!compact && (
          <button
            className="utility-button utility-icon-button"
            aria-label="More actions"
            aria-expanded={menuOpen}
            aria-controls="toolbar-menu"
            ref={menuButton}
            onClick={() => {
              setFeedbackOpen(false);
              setMenuOpen((previous) => !previous);
            }}
          >
            <ToolbarIcon name="menu" />
          </button>
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
      <div
        className="visually-hidden"
        role={error || state?.phase === "error" ? "alert" : "status"}
      >
        {status}
      </div>
      {attention && feedbackOpen && (
        <div
          className="toolbar-feedback"
          id="toolbar-feedback"
          role="region"
          aria-label="Scan status details"
          tabIndex={-1}
          ref={feedback}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.preventDefault();
              setFeedbackOpen(false);
              statusButton.current?.focus();
            }
          }}
        >
          <p>{status}</p>
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
          {state?.hasOverlay && (
            <button
              className="toolbar-status-action"
              disabled={busy}
              onClick={() =>
                void run("set_overlay_visibility", {
                  visible: !state.overlayVisible,
                })
              }
            >
              {state.overlayVisible ? "Hide OCR overlays" : "Show OCR overlays"}
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
            disabled={busy || !state?.hasOverlay || !state.overlayVisible}
            onClick={() => void run("focus_ocr_regions")}
          >
            Focus regions
          </button>
          <button
            disabled={busy}
            onClick={() => void run("show_secondary_window", { view: "saved" })}
          >
            Saved
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
