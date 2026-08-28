import React from 'react';

import type {User} from '../types/models';
import wordmark from '../assets/text-logo.png';
import {ResetIcon, ShieldIcon} from './icons';

interface Props {
    user: User;
    onReset: () => void;
    resetting: boolean;
}

export function Topbar({user, onReset, resetting}: Props): JSX.Element {
    return (
        <header className='np-topbar'>
            <div className='np-workspace'>
                <span className='np-workspace-badge'>AC</span>
                <span><strong>Acme Systems</strong><small>Enterprise workspace</small></span>
            </div>
            <div className='np-topbar-actions'>
                <img className='np-header-wordmark' src={wordmark} alt='NoPing'/>
                <span className='np-topbar-divider'/>
                <span className='np-secure-pill'><ShieldIcon size={15}/> Permission-aware</span>
                <button className='np-icon-button' type='button' onClick={onReset} disabled={resetting} title='Reset demo workspace'>
                    <ResetIcon/>
                </button>
                <div className='np-user'>
                    <span className='np-avatar'>{user.avatar}</span>
                    <span><strong>{user.name}</strong><small>{user.title}</small></span>
                </div>
            </div>
        </header>
    );
}
