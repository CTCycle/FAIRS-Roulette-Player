import { useEffect, useRef, type RefObject } from 'react';

const FOCUSABLE_SELECTOR = [
    'button:not([disabled])',
    '[href]',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
].join(',');

export const useDialogFocus = (
    containerRef: RefObject<HTMLElement | null>,
    onEscape: () => void,
    enabled = true,
): void => {
    const onEscapeRef = useRef(onEscape);

    useEffect(() => {
        onEscapeRef.current = onEscape;
    }, [onEscape]);

    useEffect(() => {
        if (!enabled) {
            return undefined;
        }

        const container = containerRef.current;
        if (!container) {
            return undefined;
        }

        const previousFocus = document.activeElement instanceof HTMLElement
            ? document.activeElement
            : null;
        const focusable = () => Array.from(
            container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
        );
        const firstFocusable = focusable()[0];
        firstFocusable?.focus();

        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                onEscapeRef.current();
                return;
            }

            if (event.key !== 'Tab') {
                return;
            }

            const currentFocusable = focusable();
            if (currentFocusable.length === 0) {
                event.preventDefault();
                container.focus();
                return;
            }

            const first = currentFocusable[0];
            const last = currentFocusable[currentFocusable.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            previousFocus?.focus();
        };
    }, [containerRef, enabled]);
};
