import React from 'react';

import type {RegistryResponse} from '../types/models';
import {NetworkIcon, ShieldIcon} from './icons';
import {humanize} from '../utils/format';

interface Props {
    registry?: RegistryResponse | null;
}

export function RegistryPage({registry}: Props): JSX.Element {
    return (
        <div className='np-page'>
            <div className='np-page-intro'><span>Enterprise fleet</span><h1>Agent registry</h1><p>Every delegate has an identity, capability boundary, data scope, status, and audit trail.</p></div>
            <div className='np-registry-summary'><div><NetworkIcon size={25}/><span><strong>{registry?.delegates.length || 0}</strong><small>Registered delegates</small></span></div><div><ShieldIcon size={25}/><span><strong>Zero trust</strong><small>Scopes checked per request</small></span></div><div><span className='np-registry-pulse'/><span><strong>Healthy</strong><small>Gateway and routing</small></span></div></div>
            <div className='np-registry-table'>
                <div className='np-registry-row is-header'><span>Delegate</span><span>Type</span><span>Capabilities</span><span>Data scope</span><span>Status</span></div>
                {(registry?.delegates || []).map((delegate) => (
                    <div className='np-registry-row' key={delegate.id}>
                        <span><i>{delegate.name.slice(0, 2).toUpperCase()}</i><strong>{delegate.name}</strong><small>{delegate.id}</small></span>
                        <span><b>{humanize(delegate.kind)}</b></span>
                        <span>{delegate.capabilities.slice(0, 2).map(humanize).join(' · ')}</span>
                        <span>{delegate.data_scopes.slice(0, 2).join(' · ')}</span>
                        <span><em className={`is-${delegate.status}`}/>{humanize(delegate.status)}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
