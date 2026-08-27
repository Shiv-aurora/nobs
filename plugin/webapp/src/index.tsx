import React from 'react';

import {App} from './App';
import './styles/noping.css';
import type {PluginRegistry} from './types/mattermost';

function NoPingGlyph(): JSX.Element {
    return <span style={{fontWeight: 800, fontSize: 16}}>N</span>;
}

export default class NoPingPlugin {
    public initialize(registry: PluginRegistry): void {
        registry.registerCustomRoute('/noping', App);
        registry.registerMainMenuAction('Open NoPing', () => {
            window.location.assign('/noping');
        });
        registry.registerChannelHeaderButtonAction(<NoPingGlyph/>, () => {
            window.location.assign('/noping');
        }, 'Ask your company');
        registry.registerWebSocketEventHandler('custom_com.noping.enterprise_run_update', () => {
            window.dispatchEvent(new CustomEvent('noping:run-update'));
        });
        registry.registerWebSocketEventHandler('custom_com.noping.enterprise_decision_update', () => {
            window.dispatchEvent(new CustomEvent('noping:decision-update'));
        });
    }
}
