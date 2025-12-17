import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import './MainLayout.css';

const MainLayout: React.FC = () => {
    return (
        <div className="main-layout">
            <Sidebar />
            <main className="content-area">
                <Outlet />
            </main>
        </div>
    );
};

export default MainLayout;
