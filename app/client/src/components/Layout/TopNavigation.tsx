import React from 'react';
import { BrainCircuit, LayoutDashboard } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const TopNavigation: React.FC = () => {
    return (
        <nav className="app-shell-nav-inner" aria-label="Primary">
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
    );
};

export default TopNavigation;
