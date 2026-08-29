import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';

import {api} from '../api/client';

export function OOOProfileAction(): JSX.Element {
    const [enabled, setEnabled] = useState(false);
    const [busy, setBusy] = useState(false);
    const [digestTotal, setDigestTotal] = useState(0);

    useEffect(() => {
        void api.bootstrap().then((value) => setEnabled(value.current_user.availability.status === 'out_of_office')).catch(() => undefined);
    }, []);

    const toggle = async () => {
        setBusy(true);
        try {
            const until = new Date(Date.now() + (3 * 24 * 60 * 60 * 1000)).toISOString();
            await api.setOOO(!enabled, !enabled ? until : undefined, !enabled ? 'daniel' : undefined);
            if (enabled) {
                const digest = await api.oooDigest();
                setDigestTotal(digest.total);
            }
            setEnabled(!enabled);
        } finally {
            setBusy(false);
        }
    };

    return <button className='nobs-profile-action' role='menuitem' type='button' onClick={() => void toggle()} disabled={busy}>
        <span className='nobs-profile-action__mark'/>
        <span><strong>{enabled ? 'End OOO mode' : 'Set OOO mode'}</strong><small>{enabled ? 'Your agent is handling routine work' : digestTotal ? `${digestTotal} handled item${digestTotal === 1 ? '' : 's'} in your return digest` : 'Let your agent handle routine work'}</small></span>
    </button>;
}

/** Inserts OOO into the signed-in user's native account menu. */
export function installAccountMenuOOOBridge(): void {
    const sync = () => {
        const menus = Array.from(document.querySelectorAll<HTMLElement>('[role="menu"]'));
        const accountMenu = menus.find((menu) => menu.textContent?.includes('Set custom status') && menu.textContent?.includes('Log out'));
        if (!accountMenu || accountMenu.querySelector('.nobs-account-menu-slot')) {
            return;
        }
        const slot = document.createElement('div');
        slot.className = 'nobs-account-menu-slot';
        slot.setAttribute('role', 'none');
        const profileItem = Array.from(accountMenu.querySelectorAll<HTMLElement>('[role="menuitem"]')).find((item) => item.textContent?.trim() === 'Profile');
        accountMenu.insertBefore(slot, profileItem || null);
        createRoot(slot).render(<OOOProfileAction/>);
    };
    const observer = new MutationObserver(sync);
    observer.observe(document.body, {childList: true, subtree: true});
    sync();
}
