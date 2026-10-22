export type PopupIconName =
  | "words"
  | "select"
  | "edit"
  | "copy"
  | "bookmark"
  | "translate"
  | "check"
  | "loading"
  | "retry"
  | "close"
  | "collapse";

const paths: Record<PopupIconName, string[]> = {
  words: ["M4 5h16M4 12h10M4 19h16"],
  select: ["M8 4H4v4m12-4h4v4M4 16v4h4m12-4v4h-4M9 8h6m-3 0v8m-3 0h6"],
  edit: ["m15 4 5 5M4 20l1-6L16 3l5 5-11 11-6 1Z"],
  copy: ["M9 9h11v12H9V9Z", "M15 9V3H3v12h6"],
  bookmark: ["M6 3h12v18l-6-4-6 4V3Z"],
  translate: [
    "M3 5h12M9 2v3m-4 3c1 4 4 7 8 9M13 5c-1 6-5 10-10 12",
    "m13 21 4-11 4 11m-6-4h4",
  ],
  check: ["m5 12 4 4L20 5"],
  loading: ["M12 3a9 9 0 1 1-9 9"],
  retry: ["M20 10a8 8 0 1 0-2 8M20 3v7h-7"],
  close: ["m6 6 12 12M18 6 6 18"],
  collapse: ["m6 15 6-6 6 6"],
};

/** Application-owned line icons; all action states retain a text label. */
export function PopupIcon({ name }: { name: PopupIconName }) {
  return (
    <svg
      className={name === "loading" ? "popup-loading-icon" : undefined}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name].map((d, index) => (
        <path d={d} key={index} />
      ))}
    </svg>
  );
}
