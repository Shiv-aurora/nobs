import React from 'react';

import logo from '../assets/logo.png';
import {HomeIcon, InboxIcon, PeopleIcon, RoomIcon} from './icons';

export type View = 'messages' | 'home' | 'ask' | 'needs' | 'projects' | 'people' | 'registry' | 'audit' | 'system';

interface Props {
    active: View;
    needsCount: number;
    onNavigate: (view: View) => void;
}

const items: Array<{id: View; label: string; icon: React.ReactNode}> = [
    {id: 'messages', label: 'Messages', icon: <RoomIcon/>},
    {id: 'needs', label: 'Needs you', icon: <InboxIcon/>},
    {id: 'people', label: 'People', icon: <PeopleIcon/>},
    {id: 'home', label: 'Insights', icon: <HomeIcon/>},
];

export function Sidebar({active, needsCount, onNavigate}: Props): JSX.Element {
    return (
        <aside className='np-sidebar'>
            <button type='button' className='np-rail-logo' onClick={() => onNavigate('messages')} aria-label='NoPing messages'><img src={logo} alt=''/></button>
            <nav className='np-nav' aria-label='NoPing navigation'>
                {items.map((item) => (
                    <button
                        type='button'
                        className={`np-nav-item ${active === item.id ? 'is-active' : ''}`}
                        onClick={() => onNavigate(item.id)}
                        key={item.id}
                        title={item.label}
                    >
                        <span className='np-nav-icon'>{item.icon}</span>
                        <small>{item.label}</small>
                        {item.id === 'needs' && needsCount > 0 && <span className='np-nav-count'>{needsCount}</span>}
                    </button>
                ))}
            </nav>
            <div className='np-sidebar-spacer'/>
            <span className='np-rail-status' title='Agent network healthy'/>
        </aside>
    );
}
