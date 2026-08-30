import React, {useEffect} from 'react';
import {createRoot} from 'react-dom/client';

const COOKIE_NAME = 'NOBSDEMONOTICE';
const NOTICE_LIFETIME_MS = 12_000;

function hasDemoNoticeCookie(): boolean {
    return document.cookie.split(';').some((part) => part.trim().startsWith(`${COOKIE_NAME}=`));
}

function clearDemoNoticeCookie(): void {
    const secure = window.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = `${COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Lax${secure}`;
}

type Props = {
    onDismiss: () => void;
};

function DemoModeNotice({onDismiss}: Props): JSX.Element {
    useEffect(() => {
        const timeout = window.setTimeout(onDismiss, NOTICE_LIFETIME_MS);
        return () => window.clearTimeout(timeout);
    }, [onDismiss]);

    return (
        <aside className='nobs-demo-notice' role='dialog' aria-modal='false' aria-labelledby='nobs-demo-notice-title'>
            <div className='nobs-demo-notice__icon' aria-hidden='true'>D</div>
            <div className='nobs-demo-notice__body'>
                <span className='nobs-demo-notice__eyebrow'>Demo mode · 12-hour session</span>
                <h2 id='nobs-demo-notice-title'>You’re exploring the NoBS demo</h2>
                <p>You’re signed in as Maya in a seeded Acme workspace. Explore Workrooms, Calendar, and permission-aware agents.</p>
            </div>
            <button className='nobs-demo-notice__dismiss' type='button' onClick={onDismiss} aria-label='Dismiss demo mode notice'>Got it</button>
        </aside>
    );
}

export function installDemoModeNotice(): void {
    if (!hasDemoNoticeCookie() || document.getElementById('nobs-demo-notice-root')) {
        return;
    }

    const slot = document.createElement('div');
    slot.id = 'nobs-demo-notice-root';
    document.body.appendChild(slot);
    const root = createRoot(slot);
    const dismiss = (): void => {
        clearDemoNoticeCookie();
        slot.classList.add('is-leaving');
        window.setTimeout(() => {
            root.unmount();
            slot.remove();
        }, 180);
    };
    root.render(<DemoModeNotice onDismiss={dismiss}/>);
}
