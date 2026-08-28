import React from 'react';

import type {RouteStep} from '../types/models';
import {CheckIcon} from './icons';

interface Props {
    route: RouteStep[];
}

const liveRoute = [
    {name: 'You', detail: 'Question received'},
    {name: 'Atlas Agent', detail: 'Project context'},
    {name: 'Engineering Agent', detail: 'Delivery evidence'},
    {name: 'Sarah Agent', detail: 'Ownership and availability'},
    {name: 'Security Agent', detail: 'Policy boundary'},
];

function initials(name: string): string {
    return name.split(' ').filter((word) => !['Delegate', 'Gate'].includes(word)).slice(0, 2).map((word) => word[0]).join('');
}

export function RouteTrace({route}: Props): JSX.Element {
    const visualRoute = [{delegate_id: 'you', delegate_name: 'You', outcome: 'Question received', duration_ms: 0}, ...route];
    return (
        <div className='np-route'>
            <div className='np-section-label'><span>Organizational route</span><small><strong>{route.length} agents consulted</strong> · 0 humans interrupted</small></div>
            <div className='np-route-rail'>
                {visualRoute.map((step, index) => (
                    <React.Fragment key={step.delegate_id}>
                        <div className={`np-route-node ${index === 0 ? 'is-you' : ''}`} style={{animationDelay: `${index * 120}ms`}}>
                            <span className='np-route-avatar'>{initials(step.delegate_name)}</span>
                            <span className='np-route-status'><CheckIcon size={12}/></span>
                            <div className='np-route-tooltip'><strong>{step.delegate_name}</strong><span>{step.outcome}</span><small>{step.duration_ms}ms</small></div>
                        </div>
                        {index < visualRoute.length - 1 && <span className='np-route-line' style={{animationDelay: `${index * 120 + 80}ms`}}/>}
                    </React.Fragment>
                ))}
            </div>
        </div>
    );
}

export function RunningRoute({query}: {query: string}): JSX.Element {
    return (
        <section className='np-running-route' aria-live='polite'>
            <div className='np-running-copy'><span>Routing now</span><h2>{query || 'Finding the right organizational context…'}</h2><p>NoPing is consulting the smallest authorized network that can answer this.</p></div>
            <div className='np-route np-route-live'>
                <div className='np-route-rail'>
                    {liveRoute.map((step, index) => (
                        <React.Fragment key={step.name}>
                            <div className={`np-route-node is-running ${index === 0 ? 'is-you' : ''}`} style={{animationDelay: `${index * 420}ms`}}>
                                <span className='np-route-avatar'>{initials(step.name)}</span>
                                <span className='np-route-pulse'/>
                                <div className='np-route-tooltip'><strong>{step.name}</strong><span>{step.detail}</span></div>
                            </div>
                            {index < liveRoute.length - 1 && <span className='np-route-line is-running' style={{animationDelay: `${index * 420 + 220}ms`}}/>}
                        </React.Fragment>
                    ))}
                </div>
            </div>
            <div className='np-running-summary'><strong>4 agents being consulted</strong><span>0 humans interrupted</span></div>
        </section>
    );
}
