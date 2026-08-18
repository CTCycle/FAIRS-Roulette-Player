import React, { useState } from 'react';
import { ArrowRight, Check, Eye, Play } from 'lucide-react';

interface TutorialMediaProps {
    variant?: 'inference-loop';
}

const stages = [
    { label: 'Play', icon: Play, copy: 'Get a prediction' },
    { label: 'Observe', icon: Eye, copy: 'Enter the wheel result' },
    { label: 'Confirm', icon: Check, copy: 'Request the next round' },
];

export const TutorialMedia: React.FC<TutorialMediaProps> = ({ variant = 'inference-loop' }) => {
    const [replayKey, setReplayKey] = useState(0);

    return (
        <div className={`guidance-media guidance-media-${variant}`} aria-label="Inference loop demonstration">
            <div className="guidance-media-viewport">
                <div className="guidance-media-track" key={replayKey}>
                    {stages.map(({ label, icon: Icon, copy }) => (
                        <div className="guidance-media-stage" key={label}>
                            <span className="guidance-media-icon"><Icon size={17} aria-hidden="true" /></span>
                            <strong>{label}</strong>
                            <span>{copy}</span>
                        </div>
                    ))}
                    <ArrowRight className="guidance-media-arrow" size={18} aria-hidden="true" />
                </div>
            </div>
            <div className="guidance-media-footer">
                <span>Short round-by-round loop</span>
                <button
                    type="button"
                    className="guidance-media-replay"
                    onClick={() => setReplayKey((key) => key + 1)}
                >
                    Replay
                </button>
            </div>
        </div>
    );
};
