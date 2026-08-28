import React from 'react';

import logo from '../assets/logo.png';

export function Logo(): JSX.Element {
    return (
        <div className='np-logo' aria-label='NoPing'>
            <img className='np-logo-symbol' src={logo} alt=''/>
            <span className='np-logo-copy'><strong>NoPing</strong><small>Organizational intelligence</small></span>
        </div>
    );
}
