import React from 'react';

import type {HealthResponse, MetricsResponse} from '../types/models';
import {ShieldIcon, SparkIcon} from './icons';

interface Props {
    health: HealthResponse | null;
    metrics: MetricsResponse | null;
}

function number(value: number | undefined): string {
    return new Intl.NumberFormat('en-US').format(value || 0);
}

export function SystemPage({health, metrics}: Props): JSX.Element {
    const modelCalls = metrics?.model_calls || 0;
    const callBudget = 200;
    const tokenBudget = 1_000_000;
    const tokenUse = metrics?.model_input_tokens || 0;
    const callPercent = Math.min(100, Math.round((modelCalls / callBudget) * 100));
    const tokenPercent = Math.min(100, Math.round((tokenUse / tokenBudget) * 100));

    return (
        <div className='np-page np-system-page'>
            <div className='np-page-intro'>
                <span>Production controls</span>
                <h1>Agent operations</h1>
                <p>Runtime health, cost boundaries, identity isolation, and evidence that NoPing fails closed.</p>
            </div>
            <div className='np-system-status-grid'>
                <section className='np-system-status-card'>
                    <span className='np-system-icon is-green'><SparkIcon/></span>
                    <div><span>Agent runtime</span><strong>{health?.status === 'ok' ? 'Healthy' : 'Unavailable'}</strong><small>{health?.mode || 'Unknown mode'} · v{health?.version || '—'}</small></div>
                </section>
                <section className='np-system-status-card'>
                    <span className='np-system-icon is-blue'><ShieldIcon/></span>
                    <div><span>AI admission</span><strong>{health?.ai_enabled ? 'Enabled' : 'Paused safely'}</strong><small>Policy, memory, permission checks, and Rooms remain available</small></div>
                </section>
                <section className='np-system-status-card'>
                    <span className='np-system-icon is-violet'>{metrics?.delegates || 0}</span>
                    <div><span>Registered delegates</span><strong>{number(metrics?.delegates)}</strong><small>Personal, project, team, policy, router, and authority identities</small></div>
                </section>
            </div>
            <div className='np-system-columns'>
                <section className='np-system-panel'>
                    <div className='np-system-panel-head'><span>Hard daily ceilings</span><strong>Cost control</strong></div>
                    <div className='np-budget-row'>
                        <div><span>Gemini calls</span><strong>{modelCalls} / {callBudget}</strong></div>
                        <div className='np-budget-track'><span style={{width: `${callPercent}%`}}/></div>
                        <small>{callPercent}% consumed · preflight admission blocks overspend</small>
                    </div>
                    <div className='np-budget-row'>
                        <div><span>Input tokens</span><strong>{number(tokenUse)} / 1,000,000</strong></div>
                        <div className='np-budget-track'><span style={{width: `${tokenPercent}%`}}/></div>
                        <small>{tokenPercent}% consumed · provider usage reconciled after each call</small>
                    </div>
                    <div className='np-cost-guard-note'><ShieldIcon size={17}/><span><strong>{metrics?.model_budget_blocks || 0} calls blocked before spend</strong><small>Cloud Run is capped at one instance; new AI work stops when limits are reached.</small></span></div>
                </section>
                <section className='np-system-panel'>
                    <div className='np-system-panel-head'><span>Operational proof</span><strong>Safety counters</strong></div>
                    <div className='np-proof-grid'>
                        <div><strong>{number(metrics?.poisoned_sources_blocked)}</strong><span>Poisoned sources quarantined</span></div>
                        <div><strong>{number(metrics?.restricted_requests_blocked)}</strong><span>Restricted requests stopped</span></div>
                        <div><strong>{number(metrics?.cache_hits)}</strong><span>Decision memories reused</span></div>
                        <div><strong>{number(metrics?.active_runs)}</strong><span>Active model runs</span></div>
                    </div>
                    <div className='np-runtime-contracts'>
                        <span>HMAC-signed plugin traffic</span>
                        <span>OIDC-authenticated Pub/Sub</span>
                        <span>Permission-filtered evidence</span>
                        <span>Scoped decision memory</span>
                    </div>
                </section>
            </div>
        </div>
    );
}
