import React from 'react';
import { Outlet } from 'react-router-dom';
import HeaderBar from './HeaderBar';
import './MainLayout.css';

const MainLayout: React.FC = () => {
    return (
        <div className="main-layout">
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
