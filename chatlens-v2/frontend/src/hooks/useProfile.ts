import { useNativeQuery } from './useNativeQuery';
import { ProfileData, profileResponseSchema } from '@/lib/schemas/profile';

export interface UseProfileResult {
  data: ProfileData | null;
  isLoading: boolean;
  error: Error | null;
  mutate: () => Promise<void>;
}

async function profileFetcher(url: unknown) {
  const res = await fetch(`${url as string}?t=${Date.now()}`, {
    signal: AbortSignal.timeout(15000),
  });
  const contentType = res.headers.get('content-type') || '';
  if (res.status === 401) {
    throw new Error('Session expired. Please log in again.');
  }
  if (!contentType.includes('application/json')) {
    throw new Error('Session expired or invalid server response');
  }
  const json = await res.json();
  const parsed = profileResponseSchema.safeParse(json);
  if (!parsed.success || !json.success) {
    throw new Error(json.error || 'Failed to fetch student profile');
  }
  return json.data || null;
}

export function useProfile(): UseProfileResult {
  const { data, error, isLoading, mutate } = useNativeQuery<ProfileData | null>(
    '/api/erp-proxy/profile',
    profileFetcher
  );

  return {
    data: data || null,
    isLoading,
    error: error || null,
    mutate,
  };
}
