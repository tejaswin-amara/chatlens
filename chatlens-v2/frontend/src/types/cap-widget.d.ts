import type { DetailedHTMLProps, HTMLAttributes } from 'react';
import type { CapWidget } from 'cap-widget';

declare global {
  namespace JSX {
    interface IntrinsicElements {
      'cap-widget': DetailedHTMLProps<
        HTMLAttributes<HTMLElement>,
        HTMLElement
      > & {
        ref?: React.Ref<CapWidget>;
        'data-cap-api-endpoint'?: string;
        onsolve?: (e: CustomEvent<{ token: string }>) => void;
        onprogress?: (e: CustomEvent<{ progress: number }>) => void;
        onerror?: (e: CustomEvent<{ message: string }>) => void;
      };
    }
  }
  namespace React {
    namespace JSX {
      interface IntrinsicElements {
        'cap-widget': DetailedHTMLProps<
          HTMLAttributes<HTMLElement>,
          HTMLElement
        > & {
          ref?: React.Ref<CapWidget>;
          'data-cap-api-endpoint'?: string;
          onsolve?: (e: CustomEvent<{ token: string }>) => void;
          onprogress?: (e: CustomEvent<{ progress: number }>) => void;
          onerror?: (e: CustomEvent<{ message: string }>) => void;
        };
      }
    }
  }
}

export {};
