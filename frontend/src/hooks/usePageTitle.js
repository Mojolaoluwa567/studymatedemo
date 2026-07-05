import { useEffect } from "react";

/**
 * Sets document.title for the lifetime of the page that calls it, then
 * restores the previous title on unmount - so navigating away (e.g. via
 * the sidebar) doesn't leave a stale title behind if something else also
 * manages the title independently.
 */
export default function usePageTitle(title) {
  useEffect(() => {
    const previous = document.title;
    document.title = title ? `${title} — StudyMate` : "StudyMate";
    return () => {
      document.title = previous;
    };
  }, [title]);
}
