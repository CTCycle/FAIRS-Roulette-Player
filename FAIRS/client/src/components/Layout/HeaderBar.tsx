import React from 'react';

const HeaderBar: React.FC = () => {
    return (
        <header className="app-shell-header">
            <div className="app-shell-brand">
                <img className="app-shell-logo" src="/favicon.png" alt="FAIRS logo" />
                <div className="app-shell-brand-copy">
                    <span className="app-shell-title">FAIRS Roulette Player</span>
                    <span className="app-shell-subtitle">Training and inference workspace</span>
                </div>
            </div>
        </header>
    );
};

export default HeaderBar;
