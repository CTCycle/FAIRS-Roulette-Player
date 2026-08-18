import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, X } from 'lucide-react';
import { createPortal } from 'react-dom';
import { useLocation } from 'react-router-dom';
import { useGuidance } from './GuidanceContext';
import { useDialogFocus } from './useDialogFocus';

interface TargetRect {
    top: number;
    left: number;
    width: number;
    height: number;
}

const TOUR_CARD_WIDTH = 360;
const VIEWPORT_MARGIN = 16;

const clamp = (value: number, minimum: number, maximum: number): number => (
    Math.min(Math.max(value, minimum), Math.max(minimum, maximum))
);

const useTargetRect = (selector: string | undefined): TargetRect | null => {
    const [rect, setRect] = useState<TargetRect | null>(null);
    const targetRef = useRef<HTMLElement | null>(null);

    useEffect(() => {
        if (!selector) {
            return undefined;
        }

        let animationFrame: number | null = null;
        let mounted = true;

        const update = () => {
            if (!mounted) {
                return;
            }

            const target = document.querySelector<HTMLElement>(selector);
            if (!target) {
                targetRef.current = null;
                setRect(null);
                return;
            }

            if (targetRef.current !== target) {
                targetRef.current = target;
                target.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'auto' });
            }

            const targetRect = target.getBoundingClientRect();
            setRect({
                top: targetRect.top,
                left: targetRect.left,
                width: targetRect.width,
                height: targetRect.height,
            });
        };

        const scheduleUpdate = () => {
            if (animationFrame !== null) {
                return;
            }
            animationFrame = window.requestAnimationFrame(() => {
                animationFrame = null;
                update();
            });
        };

        update();
        const observer = new MutationObserver(scheduleUpdate);
        observer.observe(document.body, { childList: true, subtree: true });
        window.addEventListener('resize', scheduleUpdate);
        window.addEventListener('scroll', scheduleUpdate, true);

        return () => {
            mounted = false;
            observer.disconnect();
            window.removeEventListener('resize', scheduleUpdate);
            window.removeEventListener('scroll', scheduleUpdate, true);
            if (animationFrame !== null) {
                window.cancelAnimationFrame(animationFrame);
            }
        };
    }, [selector]);

    return selector ? rect : null;
};

export const GuidedTour: React.FC = () => {
    const {
        activeTour,
        activeTourStep,
        nextTourStep,
        previousTourStep,
        dismissTour,
        skipTour,
    } = useGuidance();
    const location = useLocation();
    const panelRef = useRef<HTMLDivElement>(null);
    const step = activeTour?.steps[activeTourStep];
    const targetRect = useTargetRect(step?.target);
    const [viewport, setViewport] = useState({ width: 0, height: 0 });

    useDialogFocus(panelRef, dismissTour, Boolean(activeTour));

    useEffect(() => {
        if (activeTour && activeTour.route !== location.pathname) {
            dismissTour();
        }
    }, [activeTour, dismissTour, location.pathname]);

    useEffect(() => {
        if (!activeTour) {
            return undefined;
        }
        const updateViewport = () => setViewport({ width: window.innerWidth, height: window.innerHeight });
        updateViewport();
        window.addEventListener('resize', updateViewport);
        return () => window.removeEventListener('resize', updateViewport);
    }, [activeTour]);

    const getPanelStyle = useCallback((): React.CSSProperties => {
        if (!targetRect || viewport.width === 0) {
            return {};
        }

        const estimatedHeight = 245;
        const hasRoomBelow = targetRect.top + targetRect.height + estimatedHeight + VIEWPORT_MARGIN <= viewport.height;
        const hasRoomAbove = targetRect.top - estimatedHeight - VIEWPORT_MARGIN >= 0;
        const top = hasRoomBelow
            ? targetRect.top + targetRect.height + 14
            : hasRoomAbove
                ? targetRect.top - estimatedHeight - 14
                : VIEWPORT_MARGIN;
        const left = clamp(
            targetRect.left,
            VIEWPORT_MARGIN,
            viewport.width - TOUR_CARD_WIDTH - VIEWPORT_MARGIN,
        );

        return { top, left };
    }, [targetRect, viewport]);

    if (!activeTour || !step || typeof document === 'undefined') {
        return null;
    }

    const highlightStyle = targetRect
        ? {
            top: targetRect.top - 7,
            left: targetRect.left - 7,
            width: targetRect.width + 14,
            height: targetRect.height + 14,
        }
        : undefined;

    return createPortal(
        <div className="guidance-tour-layer" aria-live="polite">
            {targetRect && <div className="guidance-tour-highlight" style={highlightStyle} aria-hidden="true" />}
            <div
                ref={panelRef}
                className={`guidance-tour-panel${targetRect ? '' : ' guidance-tour-panel-centered'}`}
                style={getPanelStyle()}
                role="dialog"
                aria-modal="true"
                aria-labelledby="guidance-tour-title"
                aria-describedby="guidance-tour-body"
                tabIndex={-1}
            >
                <div className="guidance-tour-header">
                    <div>
                        <p className="guidance-tour-progress">Step {activeTourStep + 1} of {activeTour.steps.length}</p>
                        <h2 id="guidance-tour-title">{step.title}</h2>
                    </div>
                    <button
                        type="button"
                        className="guidance-icon-button"
                        onClick={dismissTour}
                        aria-label="Close walkthrough"
                        data-dialog-autofocus="true"
                    >
                        <X size={17} aria-hidden="true" />
                    </button>
                </div>
                <p id="guidance-tour-body" className="guidance-tour-body">{step.body}</p>
                <div className="guidance-tour-footer">
                    <button type="button" className="guidance-tour-skip" onClick={skipTour}>Skip walkthrough</button>
                    <div className="guidance-tour-actions">
                        <button
                            type="button"
                            className="guidance-secondary-button"
                            onClick={previousTourStep}
                            disabled={activeTourStep === 0}
                        >
                            <ArrowLeft size={15} aria-hidden="true" />
                            Back
                        </button>
                        <button type="button" className="guidance-primary-button" onClick={nextTourStep}>
                            {activeTourStep === activeTour.steps.length - 1 ? 'Done' : 'Next'}
                            <ArrowRight size={15} aria-hidden="true" />
                        </button>
                    </div>
                </div>
            </div>
        </div>,
        document.body,
    );
};
