import React from 'react';

import type {RouteStep} from '../types/models';
import {CheckIcon} from './icons';

interface Props {
    route: RouteStep[];
}

function initials(name: string): string {
    return name.split(' ').filter((word) => !['Delegate', 'Gate'].includes(word)).slice(0, 2).map((word) => word[0]).join('');
}

export function RouteTrace({route}: Props): JSX.Element {
    return (
        <div className='np-route'>
            <div className='np-section-label'><span>Agent route</span><small>{route.length} delegates consulted</small></div>
            <div className='np-route-rail'>
                {route.map((step, index) => (
                    <React.Fragment key={step.delegate_id}>
                        <div className='np-route-node' style={{animationDelay: `${index * 90}ms`}}>
                            <span className='np-route-avatar'>{initials(step.delegate_name)}</span>
                            <span className='np-route-status'><CheckIcon size={12}/></span>
                            <div className='np-route-tooltip'><strong>{step.delegate_name}</strong><span>{step.outcome}</span><small>{step.duration_ms}ms</small></div>
                        </div>
                        {index < route.length - 1 && <span className='np-route-line'/>}
                    </React.Fragment>
                ))}
            </div>
        </div>
    );
}
