'use client';

import { useEffect } from 'react';

export function ServiceWorkerRegistration() {
  useEffect(() => {
    if (
      !('serviceWorker' in navigator) ||
      window.location.protocol !== 'https:'
    )
      return;
    const register = () => {
      void navigator.serviceWorker
        .register('/sw.js')
        .catch((error: unknown) => {
          console.warn(
            '[SW] Registration failed:',
            error instanceof Error ? error.message : 'Unknown error'
          );
        });
    };
    window.addEventListener('load', register, { once: true });
    return () => window.removeEventListener('load', register);
  }, []);

  return null;
}
