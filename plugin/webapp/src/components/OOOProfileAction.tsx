import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';

import {api} from '../api/client';

const OOO_CHANGED_EVENT = 'nobs:ooo-changed';
const PREVIEW_BANNER_COPY = 'Preview Mode: Email notifications have not been configured.';

type OOOChange = {enabled: boolean; digestTotal?: number};

function broadcastOOO(detail: OOOChange): void {
    window.dispatchEvent(new CustomEvent<OOOChange>(OOO_CHANGED_EVENT, {detail}));
}

function useOOOControl(): {
    enabled: boolean;
    busy: boolean;
    digestTotal: number;
    toggle: () => Promise<void>;
} {
    const [enabled, setEnabled] = useState(false);
    const [busy, setBusy] = useState(false);
    const [digestTotal, setDigestTotal] = useState(0);

    useEffect(() => {
        void api.bootstrap().then((value) => setEnabled(value.current_user.availability.status === 'out_of_office')).catch(() => undefined);
        const onChanged = (event: Event) => {
            const detail = (event as CustomEvent<OOOChange>).detail;
            setEnabled(detail.enabled);
            if (typeof detail.digestTotal === 'number') {
                setDigestTotal(detail.digestTotal);
            }
        };
        window.addEventListener(OOO_CHANGED_EVENT, onChanged);
        return () => window.removeEventListener(OOO_CHANGED_EVENT, onChanged);
    }, []);

    const toggle = async () => {
        setBusy(true);
        try {
            const nextEnabled = !enabled;
            const until = new Date(Date.now() + (3 * 24 * 60 * 60 * 1000)).toISOString();
            await api.setOOO(nextEnabled, nextEnabled ? until : undefined, nextEnabled ? 'daniel' : undefined);
            let nextDigestTotal = digestTotal;
            if (!nextEnabled) {
                const digest = await api.oooDigest();
                nextDigestTotal = digest.total;
            }
            setEnabled(nextEnabled);
            setDigestTotal(nextDigestTotal);
            broadcastOOO({enabled: nextEnabled, digestTotal: nextDigestTotal});
        } finally {
            setBusy(false);
        }
    };

    return {enabled, busy, digestTotal, toggle};
}

export function OOOProfileAction(): JSX.Element {
    const {enabled, busy, digestTotal, toggle} = useOOOControl();

    return <button className='nobs-profile-action' role='menuitem' type='button' onClick={() => void toggle()} disabled={busy}>
        <span className={`nobs-profile-action__mark${enabled ? ' is-active' : ''}`}/>
        <span><strong>{enabled ? 'End OOO coverage' : 'Turn on OOO coverage'}</strong><small>{enabled ? 'Your agent is replying to routine messages' : digestTotal ? `${digestTotal} handled item${digestTotal === 1 ? '' : 's'} in your return digest` : 'Let your agent cover messages while you are away'}</small></span>
    </button>;
}

function OOOHeaderButton(): JSX.Element {
    const {enabled, busy, toggle} = useOOOControl();
    const [showConfirmation, setShowConfirmation] = useState(false);

    const onToggle = async () => {
        const nextEnabled = !enabled;
        await toggle();
        setShowConfirmation(nextEnabled);
    };

    return <div className={`nobs-ooo-header${enabled ? ' is-active' : ''}`}>
        <button
            className='nobs-ooo-header__button'
            type='button'
            aria-pressed={enabled}
            aria-label={enabled ? 'OOO coverage is on. Your agent is replying to routine messages.' : 'Turn on out-of-office agent coverage'}
            title={enabled ? 'Your agent is covering routine messages' : 'Turn on OOO coverage'}
            disabled={busy}
            onClick={() => void onToggle()}
        >
            <strong>OOO</strong>
            {enabled && <span>Agent covering</span>}
        </button>
        {enabled && showConfirmation && <div className='nobs-ooo-header__notice' role='status'>
            <button type='button' aria-label='Dismiss OOO confirmation' onClick={() => setShowConfirmation(false)}>×</button>
            <strong>Your agent has you covered</strong>
            <span>Routine messages will get a reply. Anything needing your judgment will wait in your return digest.</span>
        </div>}
    </div>;
}

function findGlobalHeader(): HTMLElement | null {
    return document.querySelector<HTMLElement>('#global-header, .global-header, header[class*="GlobalHeader"]');
}

function removeProductResidue(): void {
    const trial = document.querySelector<HTMLElement>('#startTrial');
    if (trial) {
        trial.style.display = 'none';
        trial.setAttribute('aria-hidden', 'true');
    }
    for (const child of Array.from(document.querySelectorAll<HTMLElement>('#root > div'))) {
        if (child.textContent?.includes(PREVIEW_BANNER_COPY)) {
            child.style.display = 'none';
            child.setAttribute('aria-hidden', 'true');
        }
    }
}

/** Inserts visible OOO coverage in the native global header and removes two
 * infrastructure-only notices from ordinary product chrome. */
export function installProductChromeBridge(): void {
    const sync = () => {
        removeProductResidue();
        const header = findGlobalHeader();
        if (!header || header.querySelector('.nobs-ooo-header-slot')) {
            return;
        }
        const slot = document.createElement('div');
        slot.className = 'nobs-ooo-header-slot';

        const controls = header.querySelector<HTMLElement>('#RightControlsContainer');
        const candidates = Array.from(header.querySelectorAll<HTMLElement>('button, a'));
        const mentions = candidates.find((item) => `${item.getAttribute('aria-label') || ''} ${item.getAttribute('title') || ''}`.toLowerCase().includes('mention'));
        const account = candidates.find((item) => /account|profile|user menu/.test(`${item.getAttribute('aria-label') || ''} ${item.getAttribute('title') || ''}`.toLowerCase()));
        let anchor = mentions || account;
        while (anchor?.parentElement && anchor.parentElement !== controls) {
            anchor = anchor.parentElement;
        }
        if (controls && anchor) {
            controls.insertBefore(slot, anchor);
        } else if (controls) {
            controls.insertBefore(slot, controls.firstElementChild);
        } else {
            header.appendChild(slot);
        }
        createRoot(slot).render(<OOOHeaderButton/>);
    };
    const observer = new MutationObserver(sync);
    observer.observe(document.body, {childList: true, subtree: true});
    sync();
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

/** Marks fixture-backed OOO teammates in the native DM list without replacing
 * Mattermost's sidebar. Presence remains owned by Mattermost; this compact
 * status adds why an offline teammate is still covered. */
export function installDemoOOOPresenceBridge(): void {
    const sync = () => {
        const danielLinks = Array.from(document.querySelectorAll<HTMLAnchorElement>('a[href*="/messages/@daniel"]'));
        for (const link of danielLinks) {
            link.classList.add('nobs-sidebar-user-ooo');
            link.querySelectorAll<HTMLElement>('[aria-label*="online" i], [title="Online"], [data-testid*="status"]')
                .forEach((status) => status.classList.add('nobs-ooo-native-status'));
            const label = link.querySelector<HTMLElement>('.SidebarChannelLinkLabel_wrapper');
            if (label && !label.querySelector('.nobs-sidebar-ooo-badge')) {
                const badge = document.createElement('span');
                badge.className = 'nobs-sidebar-ooo-badge';
                badge.textContent = 'OOO';
                badge.setAttribute('role', 'status');
                badge.setAttribute('aria-label', 'Daniel is out of office; his agent is covering routine messages');
                label.appendChild(badge);
            }
        }

        if (!window.location.pathname.includes('/messages/@daniel')) {
            return;
        }
        const headerTitle = document.querySelector<HTMLElement>('#channelHeaderTitle, [data-testid="channel-header-title"], .channel-header__channel-name');
        const header = headerTitle?.closest<HTMLElement>('header, #channel-header, .channel-header') || document.querySelector<HTMLElement>('#channel-header');
        if (headerTitle && !headerTitle.querySelector('.nobs-channel-ooo-badge')) {
            const badge = document.createElement('span');
            badge.className = 'nobs-channel-ooo-badge';
            badge.textContent = 'OOO · agent covering';
            badge.setAttribute('role', 'status');
            badge.setAttribute('aria-label', 'Daniel is out of office; his agent is available');
            headerTitle.appendChild(badge);
        }
        header?.querySelectorAll<HTMLElement>('[aria-label*="online" i], [title="Online"], [data-testid*="status"]')
            .forEach((status) => status.classList.add('nobs-ooo-native-status'));
    };
    const observer = new MutationObserver(sync);
    observer.observe(document.body, {childList: true, subtree: true});
    sync();
}
