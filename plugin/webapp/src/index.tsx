import React from 'react';

import {App} from './App';
import './styles/noping.css';
import type {PluginRegistry} from './types/mattermost';
import {sitePath, teamScopedNoPingPath} from './utils/navigation';

function NoPingGlyph(): JSX.Element {
    return <span style={{fontWeight: 800, fontSize: 16}}>N</span>;
}

function EmptyHeader(): null {
    return null;
}

export default class NoPingPlugin {
    public initialize(registry: PluginRegistry): void {
        let openNoPing: () => void;

        if (registry.registerProduct) {
            // NoPing is a first-class product surface, not a chatbot pane bolted onto a channel.
            registry.registerProduct(
                '/noping',
                <NoPingGlyph/>,
                'NoPing',
                '/noping',
                App,
                EmptyHeader,
                EmptyHeader,
                true,
            );
            openNoPing = () => window.location.assign(sitePath('/noping'));
        } else if (registry.registerNeedsTeamRoute) {
            registry.registerNeedsTeamRoute('/noping', App);
            openNoPing = () => window.location.assign(teamScopedNoPingPath());
        } else {
            registry.registerCustomRoute('/noping', App);
            openNoPing = () => window.location.assign(sitePath('/noping'));
        }

        registry.registerMainMenuAction('Open NoPing', openNoPing);
        registry.registerChannelHeaderButtonAction(
            <NoPingGlyph/>,
            openNoPing,
            'Ask your company',
            'Ask your company',
        );
        registry.registerWebSocketEventHandler('custom_com.noping.enterprise_run_update', () => {
            window.dispatchEvent(new CustomEvent('noping:run-update'));
        });
        registry.registerWebSocketEventHandler('custom_com.noping.enterprise_decision_update', () => {
            window.dispatchEvent(new CustomEvent('noping:decision-update'));
        });
    }
}

declare global {
    interface Window {
        registerPlugin(pluginID: string, plugin: NoPingPlugin): void;
    }
}

window.registerPlugin('com.noping.enterprise', new NoPingPlugin());
