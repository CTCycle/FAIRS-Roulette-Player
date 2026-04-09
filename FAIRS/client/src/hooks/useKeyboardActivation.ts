import { useCallback } from 'react';
import type { KeyboardEventHandler } from 'react';

export const useKeyboardActivation = (
    onActivate: () => void,
): KeyboardEventHandler<HTMLElement> => useCallback((event) => {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        onActivate();
    }
}, [onActivate]);
