/** Identity mark for an item already in the local collection, not an action. */
export function SavedBookmark() {
  return (
    <svg
      className="library-bookmark"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 3h12v18l-6-4-6 4V3Z" />
    </svg>
  );
}
