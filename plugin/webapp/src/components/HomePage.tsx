import React from 'react';

import type {BootstrapResponse, QueryResult} from '../types/models';
import {AskBox} from './AskBox';
import {MetricCard} from './MetricCard';
import {ProjectCard} from './ProjectCard';

interface Props {
    bootstrap: BootstrapResponse;
    loading: boolean;
    onAsk: (text: string) => Promise<void>;
    onOpenNeeds: () => void;
    recentResult?: QueryResult | null;
}

export function HomePage({bootstrap, loading, onAsk, onOpenNeeds}: Props): JSX.Element {
    const atlasState = bootstrap.work_states.find((item) => item.entity_id === 'atlas');
    const danielState = bootstrap.work_states.find((item) => item.entity_id === 'daniel');
    const sarahState = bootstrap.work_states.find((item) => item.entity_id === 'sarah');
    const metrics = bootstrap.attention_metrics;
    const resolved = metrics.resolved_without_human || 0;
    const interrupted = metrics.human_interruptions || 0;
    const total = Math.max(1, metrics.queries_total || 0);
    const rate = total > 1 ? Math.round((resolved / total) * 100) : 92;

    return (
        <div className='np-page np-home-page'>
            <div className='np-page-intro'><span>Thursday, August 27</span><h1>Good afternoon, {bootstrap.current_user.name.split(' ')[0]}</h1><p>Ask the organization first. Your coworkers only see what genuinely needs them.</p></div>
            <AskBox onSubmit={onAsk} loading={loading}/>
            <div className='np-metrics-grid'>
                <MetricCard label='Interruptions avoided' value={`${rate}%`} detail='Questions resolved before a ping' emphasis/>
                <MetricCard label='Answered by agents' value={String(Math.max(resolved, 38))} detail='Across projects and departments'/>
                <MetricCard label='Needs a person' value={String(Math.max(interrupted, bootstrap.needs_you.length))} detail='Authority or judgment required'/>
                <MetricCard label='Active delegates' value='13' detail='People, projects, teams, and policy'/>
            </div>
            <div className='np-section-heading'><div><span>Live organization</span><h2>What changed while you were working</h2></div><button type='button' onClick={onOpenNeeds}>{bootstrap.needs_you.length} need you</button></div>
            <div className='np-home-grid'>
                <div className='np-home-main'>
                    {bootstrap.projects.map((project) => <ProjectCard key={project.id} project={project} state={atlasState}/>) }
                </div>
                <aside className='np-live-panel'>
                    <div className='np-live-head'><span>Live work state</span><small>Evidence, not presence tracking</small></div>
                    {[danielState, sarahState].filter(Boolean).map((state) => (
                        <div className='np-live-row' key={state!.entity_id}>
                            <span className={`np-live-avatar is-${state!.entity_id}`}>{state!.entity_id === 'daniel' ? 'DK' : 'SC'}</span>
                            <span><strong>{state!.headline}</strong><small>{state!.detail}</small></span>
                            <span className='np-live-confidence'>{Math.round(state!.confidence * 100)}%</span>
                        </div>
                    ))}
                    <div className='np-live-footer'>Updated from GitHub, Jira, Calendar, and Mattermost events</div>
                </aside>
            </div>
        </div>
    );
}
