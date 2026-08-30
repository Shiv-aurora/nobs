import React from 'react';

import {api} from './api/client';
import logo from './assets/logo.png';
import {LegacyRedirect} from './components/LegacyRedirect';
import {CalendarPage, openCalendar} from './components/CalendarPage';
import {HuddlePage} from './components/HuddlePage';
import {NoPingPanel} from './components/NoPingPanel';
import {installAccountMenuOOOBridge, installDemoOOOPresenceBridge, installProductChromeBridge, OOOProfileAction} from './components/OOOProfileAction';
import {PostIdentityBadge} from './components/PostIdentityBadge';
import {WorkroomsPage} from './components/WorkroomsPage';
import './styles/native-extension.css';
import './styles/native-panel-detail.css';
import './styles/calendar.css';
import './styles/ooo.css';
import './styles/ooo-presence.css';
import './styles/send-agent.css';
import './styles/account-menu.css';
import './styles/workrooms.css';
import type {PluginRegistry, PluginStore} from './types/mattermost';

function NoPingGlyph(): JSX.Element {
    return <img className='np-native-glyph' src={logo} alt=''/>
}

function focusNativeComposer(prefix: string): void {
    const composer = document.querySelector<HTMLElement>('#post_textbox, [data-testid="post_textbox"], .ProseMirror[contenteditable="true"]');
    if (!composer) {
        return;
    }
    composer.focus();
    if (composer instanceof HTMLTextAreaElement || composer instanceof HTMLInputElement) {
        composer.value = prefix;
    } else {
        composer.textContent = prefix;
    }
    composer.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText', data: prefix}));
}

async function askAboutPost(postID: string): Promise<void> {
    const response = await fetch(`/api/v4/posts/${encodeURIComponent(postID)}`, {credentials: 'same-origin'});
    if (!response.ok) {
        return;
    }
    const post = await response.json() as {id: string; channel_id: string; root_id?: string; message: string};
    await api.agentReply(`What should I know about this message?\n\n${post.message}`, post.channel_id, post.id, post.root_id || post.id);
}

export default class NoPingPlugin {
    public initialize(registry: PluginRegistry, store: PluginStore): void {
        registry.registerCustomRoute('/noping', LegacyRedirect);
        registry.registerCustomRoute('/nobs', LegacyRedirect);
        if (registry.registerNeedsTeamRoute) {
            registry.registerNeedsTeamRoute('/calendar', CalendarPage);
            registry.registerNeedsTeamRoute('/huddle/:delegationId', HuddlePage);
            registry.registerNeedsTeamRoute('/workrooms', WorkroomsPage);
        } else {
            registry.registerCustomRoute('/nobs/calendar', CalendarPage);
            registry.registerCustomRoute('/nobs/huddle/:delegationId', HuddlePage);
            registry.registerCustomRoute('/nobs/workrooms', WorkroomsPage);
        }
        const appBar = registry.registerAppBarComponent?.(logo, undefined, 'NoBS context', '*', NoPingPanel, 'NoBS');
        if (appBar && typeof appBar !== 'string') {
            window.addEventListener('noping:open-panel', (event: Event) => {
                const runID = (event as CustomEvent<{runID?: string}>).detail?.runID;
                if (runID) {
                    window.nopingSelectedRunID = runID;
                    window.dispatchEvent(new CustomEvent('noping:select-run', {detail: {runID}}));
                }
                store.dispatch(appBar.rhsComponent.showRHSPlugin);
            });
        }
        registry.registerPostHeaderComponent?.(PostIdentityBadge);
        registry.registerPostDropdownMenuAction?.('Ask NoBS about this', (postID: string) => void askAboutPost(postID), () => true);
        registry.registerChannelHeaderButtonAction(<NoPingGlyph/>, () => focusNativeComposer(''), 'Ask naturally', 'Write normally — NoBS routes work to the right delegate automatically');
        registry.registerMainMenuAction('Ask naturally', () => focusNativeComposer(''));
        registry.registerMainMenuAction('Open Calendar', openCalendar);
        installProductChromeBridge();
        installAccountMenuOOOBridge();
        installDemoOOOPresenceBridge();
        registry.registerPopoverUserActionsComponent?.(OOOProfileAction);
        registry.registerWebSocketEventHandler('custom_com.noping.enterprise_run_update', (message: unknown) => {
            window.dispatchEvent(new CustomEvent('noping:run-update', {detail: message}));
        });
        registry.registerWebSocketEventHandler('custom_com.noping.enterprise_decision_update', () => {
            window.dispatchEvent(new CustomEvent('noping:decision-update'));
        });
    }
}

declare global {
    interface Window {
        registerPlugin(pluginID: string, plugin: NoPingPlugin): void;
        nopingSelectedRunID?: string;
    }
}

window.registerPlugin('com.noping.enterprise', new NoPingPlugin());
