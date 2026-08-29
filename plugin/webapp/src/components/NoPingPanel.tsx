import React, {useCallback, useEffect, useMemo, useState} from 'react';

import {api, APIError} from '../api/client';
import logo from '../assets/logo.png';
import type {AuditEvent, BootstrapResponse, MetricsResponse, QueryResult} from '../types/models';
import {DecisionCard} from './DecisionCard';

type PanelView = 'context' | 'needs' | 'insights' | 'security';
const tabs: Array<{id: PanelView; label: string}> = [
    {id: 'context', label: 'Context'},
    {id: 'needs', label: 'Needs You'},
    {id: 'insights', label: 'Attention'},
    {id: 'security', label: 'Security'},
];

const delegateProfiles = [
    {key: 'sarah', name: 'Sarah Chen', role: 'Security Lead', focus: 'Closing Atlas launch risk without weakening SEC-POL-12', project: 'Project Atlas · Security readiness', blocker: 'Penetration-test report SEC-184 is still pending', availability: 'Out today · Alex holds approval authority', expertise: ['Security architecture', 'Risk exceptions', 'Data controls'], answerable: ['Atlas security status', 'Delegated approval authority', 'Relevant launch controls'], evidence: ['Calendar · OOO block', 'Security review · SEC-184', 'Authority map · Alex delegated']},
    {key: 'alex', name: 'Alex Morgan', role: 'Staff Security Engineer', focus: 'Reviewing the final Atlas security exception path', project: 'Project Atlas · Security review', blocker: 'Awaiting the penetration-test report', availability: 'Available · acting approver through 6 PM', expertise: ['Application security', 'Threat modeling', 'Security review'], answerable: ['Security gate status', 'Exception requirements', 'Approval ownership'], evidence: ['Authority map · temporary delegation', 'SEC-184 · latest review note']},
    {key: 'daniel', name: 'Daniel Kim', role: 'Mobile Engineer', focus: 'Shipping the mobile authentication fix', project: 'Project Atlas · Mobile launch', blocker: 'PR #892 requires final review', availability: 'Available · heads-down until 3 PM', expertise: ['iOS', 'Authentication', 'Mobile release'], answerable: ['AUTH-392 status', 'PR #892 evidence', 'Expected merge window'], evidence: ['GitHub · PR #892', 'Jira · AUTH-392']},
    {key: 'priya', name: 'Priya Shah', role: 'Senior Product Manager', focus: 'Balancing the Northstar launch request with remaining risk', project: 'Project Atlas · Launch coordination', blocker: 'Security approval is the only open gate', availability: 'Available · next meeting at 4:30 PM', expertise: ['Product strategy', 'Enterprise launches', 'Atlas roadmap'], answerable: ['Launch scope', 'Customer impact', 'Target date and ownership'], evidence: ['Atlas plan · target date', 'Northstar account note · $200K expansion']},
];

function number(value: number | undefined): string {
    return new Intl.NumberFormat().format(value || 0);
}

export function NoPingPanel(): JSX.Element {
    const [view, setView] = useState<PanelView>('context');
    const [bootstrap, setBootstrap] = useState<BootstrapResponse | null>(null);
    const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
    const [audit, setAudit] = useState<AuditEvent[]>([]);
    const [run, setRun] = useState<QueryResult | null>(null);
    const [error, setError] = useState('');

    const refresh = useCallback(async () => {
        try {
            const [nextBootstrap, nextMetrics, nextAudit] = await Promise.all([api.bootstrap(), api.metrics(), api.audit()]);
            setBootstrap(nextBootstrap);
            setMetrics(nextMetrics);
            setAudit(nextAudit);
            setError('');
        } catch (caught) {
            setError(caught instanceof APIError ? caught.message : 'NoBS context is temporarily unavailable.');
        }
    }, []);

    useEffect(() => {
        void refresh();
        if (window.nopingSelectedRunID) {
            void api.run(window.nopingSelectedRunID).then(setRun).catch(() => undefined);
        }
        const onDecision = () => void refresh();
        const onSelectedRun = (event: Event) => {
            const runID = (event as CustomEvent<{runID?: string}>).detail?.runID;
            if (runID) {
                void api.run(runID).then(setRun).catch(() => undefined);
            }
        };
        const onRun = (event: Event) => {
            const detail = (event as CustomEvent<{data?: {run_id?: string}}>).detail;
            const runID = detail?.data?.run_id;
            if (runID) {
                void api.run(runID).then(setRun).catch(() => undefined);
            }
            void refresh();
        };
        window.addEventListener('noping:decision-update', onDecision);
        window.addEventListener('noping:select-run', onSelectedRun);
        window.addEventListener('noping:run-update', onRun);
        return () => {
            window.removeEventListener('noping:decision-update', onDecision);
            window.removeEventListener('noping:select-run', onSelectedRun);
            window.removeEventListener('noping:run-update', onRun);
        };
    }, [refresh]);

    const security = useMemo(() => audit.filter((item) => item.event_type.startsWith('security.') || item.event_type === 'query.refused'), [audit]);
    const delegateProfile = useMemo(() => {
        const route = (run?.route || []).map((step) => `${step.delegate_id} ${step.delegate_name}`.toLowerCase()).join(' ');
        return delegateProfiles.find((profile) => route.includes(profile.key));
    }, [run]);
    const resolveDecision = async (decisionID: string, status: string, rationale: string) => {
        await api.resolveDecision(decisionID, status, rationale);
        await refresh();
    };

    return <aside className='np-native-panel'>
        <header className='np-native-panel__intro'><img src={logo} alt=''/><div><strong>NoBS context</strong><span>Fewer pings. Shorter meetings.</span></div></header>
        <nav className='np-native-tabs' aria-label='NoBS panel'>{tabs.map((tab) => <button type='button' className={view === tab.id ? 'is-active' : ''} onClick={() => setView(tab.id)} key={tab.id}>{tab.label}{tab.id === 'needs' && bootstrap?.needs_you.length ? <b>{bootstrap.needs_you.length}</b> : null}</button>)}</nav>
        {error && <div className='np-panel-error'>{error}</div>}
        {view === 'context' && <div className='np-native-panel__body'>
            <section className='np-panel-section'><div className='np-section-heading'><span>Current answer</span>{run && <em>{run.status}</em>}</div>{run ? <><h3>{run.headline}</h3><p>{run.answer}</p><div className='np-attention-line'>{run.route.length} delegates consulted · {run.people_interrupted} humans interrupted</div><ol className='np-route-list'>{run.route.map((step) => <li key={`${run.run_id}-${step.ordinal}`}><i/><div><strong>{step.delegate_name}</strong><span>{step.outcome || step.reason}</span></div></li>)}</ol></> : <div className='np-panel-empty'><img src={logo} alt=''/><strong>Write normally</strong><span>In DMs and work channels, NoBS recognizes the responsible scope and lets the right employee delegate answer automatically.</span></div>}</section>
            {delegateProfile && <section className='np-panel-section np-delegate-card'><div className='np-section-heading'><span>Employee delegate</span><em>live context</em></div><div className='np-delegate-card__person'><span>{delegateProfile.name.split(' ').map((part) => part[0]).join('')}</span><div><strong>{delegateProfile.name}</strong><small>{delegateProfile.role}</small></div></div><dl><div><dt>Current focus</dt><dd>{delegateProfile.focus}</dd></div><div><dt>Project</dt><dd>{delegateProfile.project}</dd></div><div><dt>Active blocker</dt><dd>{delegateProfile.blocker}</dd></div><div><dt>Availability / OOO</dt><dd>{delegateProfile.availability}</dd></div></dl><div className='np-profile-group'><span>Expertise</span><div>{delegateProfile.expertise.map((item) => <em key={item}>{item}</em>)}</div></div><div className='np-profile-group'><span>Can answer without interrupting</span><ul>{delegateProfile.answerable.map((item) => <li key={item}>{item}</li>)}</ul></div><div className='np-profile-evidence'><span>Recent evidence</span>{delegateProfile.evidence.map((item) => <small key={item}>{item}</small>)}</div></section>}
            <section className='np-panel-section'><div className='np-section-heading'><span>Evidence</span><em>permission-aware</em></div>{run?.evidence.length ? run.evidence.map((item) => <article className='np-evidence-row' key={item.id}><strong>{item.title}</strong><span>{item.source_type} · {Math.round(item.confidence * 100)}% confidence</span></article>) : <p className='np-muted'>Evidence is shown only after access checks pass.</p>}</section>
        </div>}
        {view === 'needs' && <div className='np-native-panel__body'><section className='np-panel-section'><div className='np-section-heading'><span>Human judgment</span><em>{bootstrap?.needs_you.length || 0} open</em></div><h3>{bootstrap?.needs_you.length || 0} things actually require you</h3><p>Routine questions stay with delegates. These decisions need your authority.</p></section>{bootstrap?.needs_you.length ? bootstrap.needs_you.map((decision) => <DecisionCard key={decision.id} decision={decision} onResolve={resolveDecision}/>) : <div className='np-panel-empty'><img src={logo} alt=''/><strong>Nothing needs you</strong><span>NoBS handled the routine work without interrupting another person.</span></div>}</div>}
        {view === 'insights' && <div className='np-native-panel__body'><section className='np-panel-hero-metric'><span>Human attention saved</span><strong>{metrics ? Math.round(100 * metrics.resolved_without_human / Math.max(1, metrics.queries_total)) : 0}%</strong><p>of requests resolved without disturbing another employee</p></section><div className='np-metric-grid'><div><span>Questions</span><strong>{number(metrics?.queries_total)}</strong></div><div><span>Resolved by delegates</span><strong>{number(metrics?.resolved_without_human)}</strong></div><div><span>Human escalations</span><strong>{number(metrics?.human_interruptions)}</strong></div><div><span>Decision memories</span><strong>{number(metrics?.decision_memories)}</strong></div></div></div>}
        {view === 'security' && <div className='np-native-panel__body'><section className='np-panel-section'><div className='np-section-heading'><span>Security boundaries</span><em>{security.length} events</em></div><h3>Denied and quarantined activity</h3><p>Each event records the requesting identity, source, and enforced boundary.</p></section>{security.slice(0, 20).map((item) => <article className='np-security-row' key={item.id}><span>Blocked</span><strong>{item.summary}</strong><small>{item.actor_id} · {new Date(item.created_at).toLocaleString()}</small></article>)}{!security.length && <div className='np-panel-empty'><img src={logo} alt=''/><strong>No security events</strong><span>Permission denials and quarantined evidence will appear here.</span></div>}</div>}
    </aside>;
}
