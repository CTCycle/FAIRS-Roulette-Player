import React from 'react';

interface RouletteWheelProps {
    paused?: boolean;
}

const RouletteWheel: React.FC<RouletteWheelProps> = ({ paused = false }) => (
    <div
        className={`startup-wheel${paused ? ' startup-wheel--paused' : ''}`}
        data-testid="startup-roulette-wheel"
        aria-hidden="true"
    >
        <div className="startup-wheel__rim">
            <div className="startup-wheel__rotor">
                <span className="startup-wheel__zero-pocket">0</span>
                <div className="startup-wheel__inner-ring" />
                <div className="startup-wheel__hub">
                    <span className="startup-wheel__hub-mark" />
                </div>
            </div>
        </div>
        <div className="startup-wheel__ball-orbit">
            <span className="startup-wheel__ball" />
        </div>
    </div>
);

export default RouletteWheel;
