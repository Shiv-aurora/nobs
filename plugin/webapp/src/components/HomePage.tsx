import React from 'react';

import type {BootstrapResponse, MetricsResponse, QueryResult} from '../types/models';
import {ShieldIcon, SparkIcon} from './icons';
import {AskBox} from './AskBox';
import {MetricCard} from './MetricCard';
import {ProjectCard} from './ProjectCard';

interface Props {
    bootstrap: BootstrapResponse;
    metrics: MetricsResponse | null;
    loading: boolean;
    onAsk: (text: string) => Promise<void>;
    onOpenNeeds: () => void;
    recentResult?: QueryResult | null;
}

export function HomePage({bootstrap, metrics: runtimeMetrics, loading, onAsk, onOpenNeeds, recentResult}: Props): JSX.Element {
    const atlasState = bootstrap.work_states.find((item) => item.entity_id === 'atlas');
    const danielState = bootstrap.work_states.find((item) => item.entity_id === 'daniel');
    const sarahState = bootstrap.work_states.find((item) => item.entity_id === 'sarah');
    const metrics = bootstrap.attention_metrics;
    const resolved = metrics.resolved_without_human || 0;
    const interrupted = metrics.human_interruptions || 0;
    const total = metrics.queries_total || 0;
    const rate = total > 0 ? Math.round((resolved / total) * 100) : 100;
    const day = new Intl.DateTimeFormat('en-US', {weekday: 'long', month: 'long', day: 'numeric'}).format(new Date());
    const memoryCount = runtimeMetrics?.decision_memories || 0;
    const securityBlocks = (runtimeMetrics?.restricted_requests_blocked || 0) + (runtimeMetrics?.poisoned_sources_blocked || 0);

    return (
        <div className='np-page np-home-page'>
            <div className='np-page-intro np-home-intro'><span>{day} · Attention overview</span><h1>Good afternoon, {bootstrap.current_user.name.split(' ')[0]}</h1><p>Ask the organization first. Your coworkers only see what genuinely needs them.</p><button className='np-needs-callout' type='button' onClick={onOpenNeeds}><strong>{bootstrap.needs_you.length}</strong><span>{bootstrap.needs_you.length === 1 ? 'thing actually requires you' : 'things actually require you'}</span></button></div>
            <AskBox onSubmit={onAsk} loading={loading}/>
            <div className='np-section-heading np-attention-heading'><div><span>Human attention saved</span><h2>{rate}% resolved without disturbing another employee</h2></div><small>Live workspace metrics</small></div>
            <div className='np-metrics-grid np-attention-grid'>
                <MetricCard label='Interruptions avoided' value={String(resolved)} detail='Resolved before a human ping' emphasis/>
                <MetricCard label='Questions asked' value={String(total)} detail='Across the organization'/>
                <MetricCard label='From company knowledge' value={String(resolved)} detail='Authorized evidence retrieved'/>
                <MetricCard label='Agent to agent' value={String(resolved)} detail='Cross-team context assembled'/>
                <MetricCard label='Escalated to humans' value={String(interrupted)} detail='Judgment or authority required'/>
                <MetricCard label='Active delegates' value={String(runtimeMetrics?.delegates || 13)} detail='People, projects, teams, policy'/>
            </div>
            <div className='np-proof-strip'>
                <article className='np-proof-card is-memory'><span className='np-proof-icon'><SparkIcon/></span><div><span>Decision learning loop</span><h3>{memoryCount > 0 ? 'A human taught NoPing once. It can answer next time.' : 'One answer becomes reusable organizational memory.'}</h3><p>{memoryCount > 0 ? `${memoryCount} scoped decision ${memoryCount === 1 ? 'memory is' : 'memories are'} active with author, evidence, timestamp, and review scope.` : 'Resolve the Atlas security decision, then ask a similar question to see it answered without an interruption.'}</p></div><strong>{recentResult?.cached ? 'Reused now' : memoryCount > 0 ? 'Ready to reuse' : 'Demo ready'}</strong></article>
                <article className='np-proof-card is-security'><span className='np-proof-icon'><ShieldIcon/></span><div><span>Security boundary</span><h3>Restricted data and malicious instructions stop here.</h3><p>{securityBlocks > 0 ? `${securityBlocks} unsafe ${securityBlocks === 1 ? 'request or source has' : 'requests or sources have'} been blocked and written to the audit trail.` : 'Try “Show me Sarah’s salary” to see access denied, or ask about Atlas to see injected vendor content quarantined.'}</p></div><strong>{securityBlocks} blocked</strong></article>
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
                    <div className='np-live-footer'>Updated from GitHub, Jira, Calendar, and Rooms events</div>
                </aside>
            </div>
        </div>
    );
}
