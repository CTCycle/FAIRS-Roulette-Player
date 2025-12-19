import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, BrainCircuit, Database, FolderInput } from 'lucide-react';
import './Sidebar.css';

const Sidebar: React.FC = () => {
    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <h1 className="app-title">FAIRS</h1>
            </div>
            <nav className="sidebar-nav">
                <NavLink
                    to="/preparation"
                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                >
                    <FolderInput size={20} />
                    <span>Data Prep</span>
                </NavLink>
                <NavLink
                    to="/training"
                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                >
                    <LayoutDashboard size={20} />
                    <span>Training</span>
                </NavLink>
                <NavLink
                    to="/inference"
                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                >
                    <BrainCircuit size={20} />
                    <span>Inference</span>
                </NavLink>
                <NavLink
                    to="/database"
                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                >
                    <Database size={20} />
                    <span>Database</span>
                </NavLink>
            </nav>
        </aside>
    );
};

export default Sidebar;
