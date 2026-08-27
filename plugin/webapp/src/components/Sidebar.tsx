import React from 'react';

import {AuditIcon, HomeIcon, InboxIcon, NetworkIcon, PeopleIcon, ProjectIcon, RoomIcon, SearchIcon} from './icons';
import {Logo} from './Logo';

export type View = 'home' | 'ask' | 'needs' | 'projects' | 'people' | 'registry' | 'audit';

interface Props {
    active: View;
    needsCount: number;
    onNavigate: (view: View) => void;
}

const items: Array<{id: View; label: string; icon: React.ReactNode}> = [
    {id: 'home', label: 'Home', icon: <HomeIcon/>},
    {id: 'ask', label: 'Ask your company', icon: <SearchIcon size={19}/>},
    {id: 'needs', label: 'Needs you', icon: <InboxIcon/>},
    {id: 'projects', label: 'Projects & teams', icon: <ProjectIcon/>},
    {id: 'people', label: 'People', icon: <PeopleIcon/>},
    {id: 'registry', label: 'Agent registry', icon: <NetworkIcon/>},
    {id: 'audit', label: 'Audit trail', icon: <AuditIcon/>},
];

export function Sidebar({active, needsCount, onNavigate}: Props): JSX.Element {
    return (
        <aside className='np-sidebar'>
            <Logo/>
            <nav className='np-nav' aria-label='NoPing navigation'>
                {items.map((item) => (
                    <button
                        type='button'
                        className={`np-nav-item ${active === item.id ? 'is-active' : ''}`}
                        onClick={() => onNavigate(item.id)}
                        key={item.id}
                    >
                        <span className='np-nav-icon'>{item.icon}</span>
                        <span>{item.label}</span>
                        {item.id === 'needs' && needsCount > 0 && <span className='np-nav-count'>{needsCount}</span>}
                    </button>
                ))}
            </nav>
            <div className='np-sidebar-spacer'/>
            <a className='np-rooms-link' href='/channels/town-square'>
                <RoomIcon/>
                <span><strong>Rooms</strong><small>Human conversation</small></span>
            </a>
            <div className='np-sidebar-note'>
                <span className='np-status-dot'/>
                <span>Agent network healthy</span>
            </div>
        </aside>
    );
}
