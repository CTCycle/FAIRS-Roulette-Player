import React, { useCallback, useEffect, useId, useRef, useState } from 'react';
import { CircleHelp, X } from 'lucide-react';
import { createPortal } from 'react-dom';

interface HelpPopoverProps {
    title: string;
    children: React.ReactNode;
    label?: string;
    className?: string;
}

interface PopoverPosition {
    top: number;
    left: number;
}

const POPOVER_WIDTH = 320;
const VIEWPORT_MARGIN = 16;

const clamp = (value: number, minimum: number, maximum: number): number => (
    Math.min(Math.max(value, minimum), Math.max(minimum, maximum))
);

export const HelpPopover: React.FC<HelpPopoverProps> = ({
    title,
    children,
    label = `Explain ${title}`,
    className = '',
}) => {
    const triggerRef = useRef<HTMLButtonElement>(null);
    const popoverRef = useRef<HTMLDivElement>(null);
    const [open, setOpen] = useState(false);
    const [position, setPosition] = useState<PopoverPosition | null>(null);
    const generatedId = useId();
    const popoverId = `guidance-popover-${generatedId.replace(/:/g, '')}`;

    const updatePosition = useCallback(() => {
        const trigger = triggerRef.current;
        if (!trigger) {
            return;
        }

        const rect = trigger.getBoundingClientRect();
        const preferredTop = rect.bottom + 8;
        const estimatedHeight = 190;
        const top = preferredTop + estimatedHeight <= window.innerHeight
            ? preferredTop
            : Math.max(VIEWPORT_MARGIN, rect.top - estimatedHeight - 8);
        const left = clamp(
            rect.left,
            VIEWPORT_MARGIN,
            window.innerWidth - POPOVER_WIDTH - VIEWPORT_MARGIN,
        );
        setPosition({ top, left });
    }, []);

    useEffect(() => {
        if (!open) {
            return undefined;
        }

        updatePosition();
        const handleViewportChange = () => updatePosition();
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                setOpen(false);
                triggerRef.current?.focus();
            }
        };
        const handlePointerDown = (event: PointerEvent) => {
            const target = event.target;
            if (!(target instanceof Node)) {
                return;
            }
            if (!triggerRef.current?.contains(target) && !popoverRef.current?.contains(target)) {
                setOpen(false);
            }
        };

        window.addEventListener('resize', handleViewportChange);
        window.addEventListener('scroll', handleViewportChange, true);
        document.addEventListener('keydown', handleKeyDown);
        document.addEventListener('pointerdown', handlePointerDown);

        return () => {
            window.removeEventListener('resize', handleViewportChange);
            window.removeEventListener('scroll', handleViewportChange, true);
            document.removeEventListener('keydown', handleKeyDown);
            document.removeEventListener('pointerdown', handlePointerDown);
        };
    }, [open, updatePosition]);

    useEffect(() => {
        if (open && position) {
            popoverRef.current?.querySelector<HTMLElement>('[data-popover-autofocus="true"]')?.focus();
        }
    }, [open, position]);

    return (
        <span className={`guidance-popover-anchor ${className}`.trim()}>
            <button
                ref={triggerRef}
                type="button"
                className="guidance-help-button"
                onClick={() => setOpen((current) => !current)}
                aria-label={label}
                aria-haspopup="dialog"
                aria-expanded={open}
                aria-controls={open ? popoverId : undefined}
            >
                <CircleHelp size={16} aria-hidden="true" />
            </button>
            {open && position && typeof document !== 'undefined' && createPortal(
                <div
                    ref={popoverRef}
                    id={popoverId}
                    className="guidance-popover"
                    role="dialog"
                    aria-label={title}
                    aria-describedby={`${popoverId}-body`}
                    style={{ top: position.top, left: position.left }}
                >
                    <div className="guidance-popover-header">
                        <strong>{title}</strong>
                        <button
                            type="button"
                            className="guidance-popover-close"
                            onClick={() => {
                                setOpen(false);
                                triggerRef.current?.focus();
                            }}
                            aria-label={`Close ${title}`}
                            data-popover-autofocus="true"
                        >
                            <X size={14} aria-hidden="true" />
                        </button>
                    </div>
                    <div id={`${popoverId}-body`} className="guidance-popover-body">{children}</div>
                </div>,
                document.body,
            )}
        </span>
    );
};
