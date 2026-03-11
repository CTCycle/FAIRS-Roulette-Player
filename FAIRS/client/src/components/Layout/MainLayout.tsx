import React from 'react';
import { Outlet } from 'react-router-dom';
import HeaderBar from './HeaderBar';
import TopNavigation from './TopNavigation';
import './MainLayout.css';

const MainLayout: React.FC = () => {
    return (
        <div className="main-layout">
            <HeaderBar />
            <TopNavigation />
            <main className="content-area">
                <Outlet />
            </main>
        </div>
    );
};

export default MainLayout;
