import React from 'react';
import { ArrowRight, BookOpen, RotateCcw } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { GuidanceDialog } from './GuidanceDialog';
import { INFERENCE_TOUR, TRAINING_TOUR } from './definitions';
import { TutorialMedia } from './TutorialMedia';
import { useGuidance } from './GuidanceContext';

interface TipsAndTricksDialogProps {
    open: boolean;
    onClose: () => void;
}

export const TipsAndTricksDialog: React.FC<TipsAndTricksDialogProps> = ({ open, onClose }) => {
    const {
        tips,
        startTour,
        resetGuidance,
    } = useGuidance();
    const location = useLocation();
    const isTrainingRoute = location.pathname === TRAINING_TOUR.route;

    if (!open) {
        return null;
    }

    return (
        <GuidanceDialog
            title="Tips & Tricks"
            description="Short ways to get more from the Training and Inference workspace."
            labelledBy="tips-and-tricks-title"
            onClose={onClose}
            className="guidance-tips-dialog"
        >
            <div className="guidance-tips-scroll">
                <div className="guidance-tips-section">
                    <div className="guidance-section-heading">
                        <BookOpen size={17} aria-hidden="true" />
                        <h3>Useful shortcuts</h3>
                    </div>
                    <div className="guidance-tip-grid">
                        {tips.map((tip) => (
                            <article className="guidance-tip-card" key={tip.id}>
                                <h4>{tip.title}</h4>
                                <p>{tip.body}</p>
                            </article>
                        ))}
                    </div>
                </div>

                <TutorialMedia />

                <div className="guidance-tips-section">
                    <div className="guidance-section-heading">
                        <ArrowRight size={17} aria-hidden="true" />
                        <h3>Optional walkthroughs</h3>
                    </div>
                    <div className="guidance-tour-links">
                        {isTrainingRoute ? (
                            <button type="button" onClick={() => startTour(TRAINING_TOUR)}>
                                Restart Training walkthrough
                                <ArrowRight size={15} aria-hidden="true" />
                            </button>
                        ) : (
                            <button type="button" onClick={() => startTour(INFERENCE_TOUR)}>
                                Show the Inference loop
                                <ArrowRight size={15} aria-hidden="true" />
                            </button>
                        )}
                    </div>
                </div>
            </div>
            <div className="guidance-dialog-footer">
                <button
                    type="button"
                    className="guidance-reset-button"
                    onClick={() => {
                        resetGuidance();
                        onClose();
                    }}
                >
                    <RotateCcw size={14} aria-hidden="true" />
                    Reset guidance
                </button>
            </div>
        </GuidanceDialog>
    );
};
