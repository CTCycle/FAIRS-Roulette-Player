import React from 'react';
import { Outlet } from 'react-router-dom';
import HeaderBar from './HeaderBar';
import './MainLayout.css';

const MainLayout: React.FC = () => {
    return (
        <div className="main-layout">
            <div className="desktop-size-notice" role="alert">
                <strong>Desktop window required</strong>
                <span>FAIRS requires a browser viewport at least 1100px wide. Enlarge the window to use the full workspace.</span>
            </div>
            <div className="app-shell-top">
                <HeaderBar />
            </div>
            <main className="content-area">
                <Outlet />
            </main>
        </div>
    );
};

export default MainLayout;
