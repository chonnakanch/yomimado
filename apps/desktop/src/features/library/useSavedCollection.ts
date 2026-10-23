import { useCallback, useEffect, useRef, useState } from "react";

// Both collections use the same list/delete lifecycle, with separate hook
// instances and their existing typed clients. No storage format changes.
export function useSavedCollection<T extends { id: number }>(
  active: boolean,
  list: () => Promise<T[]>,
  deleteItem: (id: number) => Promise<void>,
  revision = 0,
) {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(active);
  const [error, setError] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<number | null>(null);
  const [removalError, setRemovalError] = useState<{
    id: number;
    message: string;
  } | null>(null);
  const [removed, setRemoved] = useState(false);
  const pendingRemoval = useRef<number | null>(null);
  const refreshAfterRemoval = useRef(false);
  const listRequest = useRef(0);
  const deleteRequest = useRef(0);
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      listRequest.current++;
      deleteRequest.current++;
    };
  }, []);

  const refresh = useCallback(async () => {
    if (pendingRemoval.current !== null) {
      refreshAfterRemoval.current = true;
      return;
    }
    const request = ++listRequest.current;
    setLoading(true);
    setError(null);
    setRemovalError(null);
    setRemoved(false);
    try {
      const next = await list();
      if (mounted.current && request === listRequest.current) setItems(next);
    } catch (error) {
      if (mounted.current && request === listRequest.current)
        setError(String(error).replace(/^Error: /, ""));
    } finally {
      if (mounted.current && request === listRequest.current) setLoading(false);
    }
  }, [list]);

  useEffect(() => {
    if (active) void refresh();
    else setLoading(false);
    return () => {
      listRequest.current++;
    };
  }, [active, refresh, revision]);

  const remove = async (item: T, confirmation: string): Promise<boolean> => {
    if (pendingRemoval.current !== null || !window.confirm(confirmation))
      return false;
    pendingRemoval.current = item.id;
    const request = ++deleteRequest.current;
    // A list started before this deletion must not put the removed row back.
    listRequest.current++;
    setLoading(false);
    setRemovingId(item.id);
    setRemovalError(null);
    setRemoved(false);
    try {
      await deleteItem(item.id);
      if (mounted.current && request === deleteRequest.current) {
        setItems((previous) =>
          previous.filter((entry) => entry.id !== item.id),
        );
        setRemoved(true);
      }
      return true;
    } catch (error) {
      if (mounted.current && request === deleteRequest.current)
        setRemovalError({
          id: item.id,
          message: String(error).replace(/^Error: /, ""),
        });
      return false;
    } finally {
      if (request === deleteRequest.current) {
        pendingRemoval.current = null;
        if (mounted.current) setRemovingId(null);
        if (mounted.current && refreshAfterRemoval.current) {
          refreshAfterRemoval.current = false;
          void refresh();
        }
      }
    }
  };

  return {
    items,
    loading,
    error,
    removingId,
    removalError,
    removed,
    refresh,
    remove,
  };
}
