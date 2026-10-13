export type ToolbarIconName =
  | "area"
  | "screen"
  | "rescan"
  | "visible"
  | "hidden"
  | "menu"
  | "expand"
  | "collapse"
  | "book";

/** Small application-owned line icons; no icon/font dependency. */
export function ToolbarIcon({ name }: { name: ToolbarIconName }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {name === "area" && <path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5" />}
      {name === "screen" && (
        <>
          <rect x="3" y="4" width="18" height="13" rx="2" />
          <path d="M12 17v4m-4 0h8" />
        </>
      )}
      {name === "rescan" && (
        <>
          <path d="M20 11a8 8 0 1 0-2 6M20 4v7h-7" />
        </>
      )}
      {(name === "visible" || name === "hidden") && (
        <>
          <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" />
          <circle cx="12" cy="12" r="3" />
          {name === "hidden" && <path d="m3 3 18 18" />}
        </>
      )}
      {name === "menu" && (
        <>
          <circle cx="5" cy="12" r="1" />
          <circle cx="12" cy="12" r="1" />
          <circle cx="19" cy="12" r="1" />
        </>
      )}
      {name === "expand" && <path d="m8 6 6 6-6 6m6-12 6 6-6 6" />}
      {name === "collapse" && <path d="m10 6-6 6 6 6m6-12-6 6 6 6" />}
      {name === "book" && (
        <path d="M12 6C8 3 5 3 2 4v15c3-1 6-1 10 2m0-15c4-3 7-3 10-2v15c-3-1-6-1-10 2V6Z" />
      )}
    </svg>
  );
}
