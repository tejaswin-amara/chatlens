import { useState, useEffect, useCallback, useRef } from 'react';

export const globalQueryCache = new Map<string, unknown>();
const inFlightDedupeMap = new Map<string, Promise<unknown>>();

export function getCacheKeyStr(key: unknown): string {
  if (key === null || key === undefined) return '';
  return typeof key === 'string' ? key : JSON.stringify(key);
}

export function getCachedValue<T>(key: unknown): T | undefined {
  const keyStr = getCacheKeyStr(key);
  if (!keyStr) return undefined;

  if (globalQueryCache.has(keyStr)) {
    return globalQueryCache.get(keyStr) as T;
  }

  if (typeof window !== 'undefined') {
    try {
      const stored = sessionStorage.getItem(`kl_cache_${keyStr}`);
      if (stored) {
        const parsed = JSON.parse(stored) as T;
        globalQueryCache.set(keyStr, parsed);
        return parsed;
      }
    } catch {
      // Ignore sessionStorage parsing or quota errors
    }
  }

  return undefined;
}

export function setCachedValue<T>(key: unknown, value: T): void {
  const keyStr = getCacheKeyStr(key);
  if (!keyStr) return;

  globalQueryCache.set(keyStr, value);

  if (typeof window !== 'undefined') {
    try {
      sessionStorage.setItem(`kl_cache_${keyStr}`, JSON.stringify(value));
    } catch {
      // Ignore quota errors
    }
  }
}

export function clearGlobalCache(): void {
  globalQueryCache.clear();
  inFlightDedupeMap.clear();
  if (typeof window !== 'undefined') {
    try {
      const keysToRemove: string[] = [];
      for (let i = 0; i < sessionStorage.length; i++) {
        const k = sessionStorage.key(i);
        if (k && k.startsWith('kl_cache_')) {
          keysToRemove.push(k);
        }
      }
      keysToRemove.forEach((k) => sessionStorage.removeItem(k));
    } catch {
      // Ignore storage errors
    }
  }
}

function fetchWithDedupe<T>(
  keyStr: string,
  fetcherFn: () => Promise<T>
): Promise<T> {
  const existing = inFlightDedupeMap.get(keyStr);
  if (existing) return existing as Promise<T>;

  const promise = fetcherFn().finally(() => {
    inFlightDedupeMap.delete(keyStr);
  });
  inFlightDedupeMap.set(keyStr, promise);
  return promise;
}

export function useNativeQuery<T>(
  key: string | null | readonly (string | null)[],
  fetcher: (key: unknown) => Promise<T>
) {
  const url = Array.isArray(key) ? key[0] : key;
  const shouldFetch =
    key !== null &&
    url !== null &&
    (Array.isArray(key) ? key.every(Boolean) : true);
  const keyStr = getCacheKeyStr(key);

  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(() =>
    Boolean(shouldFetch)
  );
  const [isStale, setIsStale] = useState(false);

  const mountedRef = useRef(true);
  const keyRef = useRef(key);

  useEffect(() => {
    keyRef.current = key;
  });

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const mutate = useCallback(async () => {
    if (!shouldFetch || !url) return;

    // Only show loading if we have no cached data at all
    const cached = getCachedValue<T>(keyRef.current);
    if (mountedRef.current && cached === undefined) {
      setIsLoading(true);
    }

    try {
      const result = await fetchWithDedupe(keyStr, () =>
        fetcher(keyRef.current)
      );
      setCachedValue(keyRef.current, result);
      if (mountedRef.current) {
        setData(result);
        setError(null);
        setIsStale(false);
      }
    } catch (err: unknown) {
      const normalizedError =
        err instanceof Error ? err : new Error(String(err));
      const isSessionError =
        /session expired|authentication required|sign in again/i.test(
          normalizedError.message
        );
      if (isSessionError) {
        clearGlobalCache();
        if (mountedRef.current) {
          setData(undefined);
          setIsStale(false);
        }
      } else if (mountedRef.current) {
        // Transient error (502, 504, network): preserve stale cached data
        const staleData = getCachedValue<T>(keyRef.current);
        if (staleData !== undefined) {
          setData(staleData);
          setIsStale(true);
        }
      }
      if (mountedRef.current) {
        setError(normalizedError);
      }
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [keyStr, shouldFetch, url, fetcher]);

  useEffect(() => {
    if (shouldFetch) {
      void mutate();
    }
  }, [mutate, shouldFetch]);

  return { data, error, isLoading, isStale, mutate };
}
