import React from 'react';
import { CircleHelp } from 'lucide-react';
import TopNavigation from './TopNavigation';
import { useGuidance } from '../guidance/GuidanceContext';

const HeaderBar: React.FC = () => {
    const { tipsOpen, openTips } = useGuidance();

    return (
        <header className="app-shell-header">
            <div className="app-shell-brand">
                <img className="app-shell-logo" src="/favicon.png" alt="FAIRS logo" />
                <div className="app-shell-brand-copy">
                    <span className="app-shell-title">FAIRS Roulette Player</span>
                    <span className="app-shell-subtitle">Training and inference workspace</span>
                </div>
            </div>
            <div className="app-shell-actions">
                <TopNavigation />
                <button
                    type="button"
                    className="app-shell-help"
                    onClick={openTips}
                    aria-haspopup="dialog"
                    aria-expanded={tipsOpen}
                >
                    <CircleHelp size={17} aria-hidden="true" />
                    <span>Help</span>
                </button>
            </div>
        </header>
    );
};

export default HeaderBar;
