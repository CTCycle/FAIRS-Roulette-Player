import React from 'react';
import { BrainCircuit, LayoutDashboard } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const TopNavigation: React.FC = () => {
    return (
        <div className="app-shell-nav" role="navigation" aria-label="Primary">
            <nav className="app-shell-nav-inner">
                <NavLink
                    to="/training"
                    className={({ isActive }) => `top-nav-link ${isActive ? 'active' : ''}`}
                >
                    <LayoutDashboard size={18} />
                    <span>Training</span>
                </NavLink>
                <NavLink
                    to="/inference"
                    className={({ isActive }) => `top-nav-link ${isActive ? 'active' : ''}`}
                >
                    <BrainCircuit size={18} />
                    <span>Inference</span>
                </NavLink>
            </nav>
        </div>
    );
};

export default TopNavigation;
