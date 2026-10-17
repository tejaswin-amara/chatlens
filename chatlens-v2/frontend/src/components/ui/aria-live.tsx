'use client';

import * as React from 'react';

interface AriaLiveContextType {
  announce: (message: string, priority?: 'polite' | 'assertive') => void;
}

const AriaLiveContext = React.createContext<AriaLiveContextType | undefined>(
  undefined
);

export function useAriaAnnounce() {
  const context = React.useContext(AriaLiveContext);
  if (!context) {
    return { announce: () => {} };
  }
  return context;
}

export function AriaLiveRegion({ children }: { children?: React.ReactNode }) {
  const [politeMessage, setPoliteMessage] = React.useState('');
  const [assertiveMessage, setAssertiveMessage] = React.useState('');

  const announce = React.useCallback(
    (message: string, priority: 'polite' | 'assertive' = 'polite') => {
      if (priority === 'assertive') {
        setAssertiveMessage(message);
        setTimeout(() => setAssertiveMessage(''), 1000);
      } else {
        setPoliteMessage(message);
        setTimeout(() => setPoliteMessage(''), 1000);
      }
    },
    []
  );

  return (
    <AriaLiveContext.Provider value={{ announce }}>
      {children}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {politeMessage}
      </div>
      <div className="sr-only" aria-live="assertive" aria-atomic="true">
        {assertiveMessage}
      </div>
    </AriaLiveContext.Provider>
  );
}
