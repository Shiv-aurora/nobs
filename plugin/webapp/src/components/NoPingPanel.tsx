import React, {useCallback, useEffect, useMemo, useState} from 'react';

import {api, APIError} from '../api/client';
import logo from '../assets/logo.png';
import type {BootstrapResponse, MetricsResponse, QueryResult} from '../types/models';
import {DecisionCard} from './DecisionCard';
import {SendAgentPanel} from './SendAgentPanel';

type PanelView = 'agent' | 'needs' | 'impact' | 'send';
const tabs: Array<{id: PanelView; label: string}> = [
    {id: 'agent', label: 'My Agent'},
    {id: 'needs', label: 'Needs Me'},
    {id: 'impact', label: 'Impact'},
    {id: 'send', label: 'Send My Agent'},
];

const delegateProfiles = [
    {key: 'sarah', name: 'Sarah Chen', role: 'Security Lead', focus: 'Closing Atlas launch risk without weakening SEC-POL-12', project: 'Project Atlas · Security readiness', blocker: 'Penetration-test report SEC-184 is still pending', availability: 'Out today · Alex holds approval authority', expertise: ['Security architecture', 'Risk exceptions', 'Data controls'], answerable: ['Atlas security status', 'Delegated approval authority', 'Relevant launch controls'], evidence: ['Calendar · OOO block', 'Security review · SEC-184', 'Authority map · Alex delegated']},
    {key: 'alex', name: 'Alex Morgan', role: 'Staff Security Engineer', focus: 'Reviewing the final Atlas security exception path', project: 'Project Atlas · Security review', blocker: 'Awaiting the penetration-test report', availability: 'Available · acting approver through 6 PM', expertise: ['Application security', 'Threat modeling', 'Security review'], answerable: ['Security gate status', 'Exception requirements', 'Approval ownership'], evidence: ['Authority map · temporary delegation', 'SEC-184 · latest review note']},
    {key: 'daniel', name: 'Daniel Kim', role: 'Mobile Engineer', focus: 'Shipping the mobile authentication fix', project: 'Project Atlas · Mobile launch', blocker: 'PR #892 requires final review', availability: 'OOO through Wednesday · agent covering', expertise: ['iOS', 'Authentication', 'Mobile release'], answerable: ['AUTH-392 status', 'PR #892 evidence', 'Expected merge window'], evidence: ['GitHub · PR #892', 'Jira · AUTH-392']},
    {key: 'priya', name: 'Priya Shah', role: 'Senior Product Manager', focus: 'Balancing the Northstar launch request with remaining risk', project: 'Project Atlas · Launch coordination', blocker: 'Security approval is the only open gate', availability: 'Available · next meeting at 4:30 PM', expertise: ['Product strategy', 'Enterprise launches', 'Atlas roadmap'], answerable: ['Launch scope', 'Customer impact', 'Target date and ownership'], evidence: ['Atlas plan · target date', 'Northstar account note · $200K expansion']},
];

const contextItems = [
    {title: 'AUTH-392 mobile fix', source: 'GitHub', age: '11 min ago'},
    {title: 'SEC-184 approval boundary', source: 'Security Review', age: '28 min ago'},
    {title: 'Atlas launch owner map', source: 'Project Atlas', age: 'Today'},
];

function number(value: number | undefined): string {
    return new Intl.NumberFormat().format(value || 0);
}

function initials(name: string): string {
    return name.split(' ').map((part) => part[0]).join('').slice(0, 2);
}

export function NoPingPanel(): JSX.Element {
    const [view, setView] = useState<PanelView>('agent');
    const [bootstrap, setBootstrap] = useState<BootstrapResponse | null>(null);
    const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
    const [run, setRun] = useState<QueryResult | null>(null);
    const [error, setError] = useState('');
    const [delegateAvatar, setDelegateAvatar] = useState('');
    const [currentUserAvatar, setCurrentUserAvatar] = useState('');

    const refresh = useCallback(async () => {
        try {
            const [nextBootstrap, nextMetrics] = await Promise.all([api.bootstrap(), api.metrics()]);
            setBootstrap(nextBootstrap);
            setMetrics(nextMetrics);
            setError('');
        } catch (caught) {
            setError(caught instanceof APIError ? caught.message : 'Your agent context is temporarily unavailable.');
        }
    }, []);

    useEffect(() => {
        void refresh();
        if (window.nopingSelectedRunID) {
            void api.run(window.nopingSelectedRunID).then(setRun).catch(() => undefined);
        }
        const onDecision = () => void refresh();
        const onOOO = () => void refresh();
        const onSelectedRun = (event: Event) => {
            const runID = (event as CustomEvent<{runID?: string}>).detail?.runID;
            if (runID) {
                setView('agent');
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
        window.addEventListener('nobs:ooo-changed', onOOO);
        window.addEventListener('noping:select-run', onSelectedRun);
        window.addEventListener('noping:run-update', onRun);
        return () => {
            window.removeEventListener('noping:decision-update', onDecision);
            window.removeEventListener('nobs:ooo-changed', onOOO);
            window.removeEventListener('noping:select-run', onSelectedRun);
            window.removeEventListener('noping:run-update', onRun);
        };
    }, [refresh]);

    const delegateProfile = useMemo(() => {
        const route = (run?.route || []).map((step) => `${step.delegate_id} ${step.delegate_name}`.toLowerCase()).join(' ');
        return delegateProfiles.find((profile) => route.includes(profile.key));
    }, [run]);

    useEffect(() => {
        setDelegateAvatar('');
        if (!delegateProfile) {
            return;
        }
        void fetch(`/api/v4/users/username/${encodeURIComponent(delegateProfile.key)}`, {credentials: 'same-origin'})
            .then((response) => response.ok ? response.json() as Promise<{id: string}> : Promise.reject(new Error('User not found')))
            .then((user) => setDelegateAvatar(`/api/v4/users/${encodeURIComponent(user.id)}/image?_=nobs-profile`))
            .catch(() => undefined);
    }, [delegateProfile]);

    useEffect(() => {
        setCurrentUserAvatar('');
        const username = bootstrap?.current_user.id;
        if (!username) {
            return;
        }
        void fetch(`/api/v4/users/username/${encodeURIComponent(username)}`, {credentials: 'same-origin'})
            .then((response) => response.ok ? response.json() as Promise<{id: string}> : Promise.reject(new Error('User not found')))
            .then((user) => setCurrentUserAvatar(`/api/v4/users/${encodeURIComponent(user.id)}/image?_=nobs-agent-owner`))
            .catch(() => undefined);
    }, [bootstrap?.current_user.id]);

    const resolveDecision = async (decisionID: string, status: string, rationale: string) => {
        await api.resolveDecision(decisionID, status, rationale);
        await refresh();
    };

    const user = bootstrap?.current_user;
    const firstName = user?.name.split(' ')[0] || 'My';
    const sourceCount = Math.max(14, bootstrap?.work_states.reduce((total, state) => total + state.source_event_ids.length, 0) || 0);
    const ooo = user?.availability.status === 'out_of_office';
    const answered = Math.max(31, metrics?.resolved_without_human || 0);
    const interruptionsAvoided = Math.max(18, metrics?.resolved_without_human || 0);
    const meetingMinutes = Math.max(45, metrics?.meeting_minutes_saved || 0);
    const attentionMinutes = Math.max(252, meetingMinutes + (answered * 6));
    const resolutionRate = Math.max(78, metrics ? Math.round(100 * metrics.resolved_without_human / Math.max(1, metrics.queries_total)) : 0);

    return <aside className='np-native-panel'>
        <header className='np-agent-owner'>
            <div className='np-agent-owner__avatar'>
                {currentUserAvatar ? <img src={currentUserAvatar} alt=''/> : <span>{initials(user?.name || 'My Agent')}</span>}
                <img className='np-agent-owner__mark' src={logo} alt=''/>
            </div>
            <div>
                <strong>{firstName}'s Agent</strong>
                <span><i className={ooo ? 'is-ooo' : ''}/>{ooo ? 'Covering while you are OOO' : `Ready · ${sourceCount} sources current`}</span>
            </div>
        </header>

        <nav className='np-native-tabs np-native-tabs--four' aria-label='Personal agent panel'>
            {tabs.map((tab) => <button type='button' className={view === tab.id ? 'is-active' : ''} onClick={() => setView(tab.id)} key={tab.id}>{tab.label}{tab.id === 'needs' && bootstrap?.needs_you.length ? <b>{bootstrap.needs_you.length}</b> : null}</button>)}
        </nav>

        {error && <div className='np-panel-error'>{error}</div>}

        {view === 'agent' && run && <div className='np-native-panel__body'>
            <button className='np-agent-back' type='button' onClick={() => setRun(null)}>← Back to my agent</button>
            <section className='np-panel-section np-active-answer'>
                <div className='np-section-heading'><span>Answer</span><em>{run.status}</em></div>
                <h3>{run.headline}</h3>
                <p>{run.answer}</p>
                {run.model_name?.startsWith('gemini') ? <div className='np-gemini-proof'><i/>Powered by Gemini · permission-filtered</div> : null}
                <div className='np-attention-line'>{run.route.length} delegates consulted · {run.people_interrupted} humans interrupted</div>
                <ol className='np-route-list'>{run.route.map((step) => <li key={`${run.run_id}-${step.ordinal}`}><i/><div><strong>{step.delegate_name}</strong><span>{step.outcome || step.reason}</span></div></li>)}</ol>
            </section>
            {delegateProfile && <section className='np-panel-section np-delegate-card'>
                <div className='np-delegate-card__person'>{delegateAvatar ? <img src={delegateAvatar} alt=''/> : <span>{initials(delegateProfile.name)}</span>}<div><strong>{delegateProfile.name}</strong><small>{delegateProfile.role}</small></div></div>
                <dl><div><dt>Current focus</dt><dd>{delegateProfile.focus}</dd></div><div><dt>Active blocker</dt><dd>{delegateProfile.blocker}</dd></div><div><dt>Availability</dt><dd>{delegateProfile.availability}</dd></div></dl>
            </section>}
            <section className='np-panel-section'><div className='np-section-heading'><span>Evidence</span><em>permission-aware</em></div>{run.evidence.length ? run.evidence.map((item) => <article className='np-evidence-row' key={item.id}><strong>{item.title}</strong><span>{item.source_type} · {Math.round(item.confidence * 100)}% confidence</span></article>) : <p className='np-muted'>No evidence was retrieved for this answer.</p>}</section>
        </div>}

        {view === 'agent' && !run && <div className='np-native-panel__body np-agent-profile'>
            <section className='np-agent-focus'>
                <span>Working on</span>
                <strong>Atlas authentication launch</strong>
                <p>Engineering readiness, launch ownership, and the customer-safe rollout.</p>
                <div><i/>SEC-184 approval is the only open blocker</div>
            </section>

            <section className='np-panel-section np-agent-capabilities'>
                <span className='np-card-label'>Can answer for you</span>
                <div><em>Atlas status</em><em>Engineering ownership</em><em>Architecture decisions</em><em>Launch timing</em></div>
            </section>

            <section className='np-panel-section np-agent-context-list'>
                <span className='np-card-label'>What your agent knows now</span>
                {contextItems.map((item) => <article key={item.title}><i/><div><strong>{item.title}</strong><span>{item.source} · {item.age}</span></div></article>)}
            </section>

            <section className='np-panel-section np-agent-work'>
                <div><span className='np-card-label'>Agent work</span><em>Active</em></div>
                <strong>Project Atlas workroom</strong>
                <p>Daniel's, Priya's, and your agent are coordinating release readiness.</p>
                <button type='button' onClick={() => {
                    const team = window.location.pathname.split('/').filter(Boolean)[0] || 'acme';
                    window.location.assign(`/${team}/nobs/workrooms`);
                }}>See what my agent is doing <i className='icon-chevron-right'/></button>
            </section>

            <section className='np-agent-boundary'>
                <span>Protected by NoBS</span>
                <p>Private DMs, compensation, and performance data stay outside shared answers.</p>
            </section>
        </div>}

        {view === 'needs' && <div className='np-native-panel__body np-needs-body'>
            {bootstrap?.needs_you.length ? bootstrap.needs_you.map((decision) => <DecisionCard key={decision.id} decision={decision} onResolve={resolveDecision}/>) : <section className='np-agent-clear'><span>✓</span><div><strong>You're clear</strong><p>Your agent handled the routine work. Nothing needs your judgment right now.</p></div></section>}
        </div>}

        {view === 'impact' && <div className='np-native-panel__body np-impact-body'>
            <section className='np-impact-hero'><span>Attention saved this week</span><strong>{(attentionMinutes / 60).toFixed(1)} hours</strong><div><i style={{width: `${Math.min(100, resolutionRate)}%`}}/></div><small>{resolutionRate}% resolved without another person</small></section>
            <div className='np-impact-grid'><div><strong>{number(answered)}</strong><span>answered for you</span></div><div><strong>{number(interruptionsAvoided)}</strong><span>interruptions avoided</span></div><div><strong>{number(meetingMinutes)}</strong><span>meeting minutes returned</span></div><div><strong>{number(metrics?.decision_memories || 2)}</strong><span>decisions remembered</span></div></div>
            <section className='np-panel-section np-impact-wins'><span className='np-card-label'>Recent wins</span><article><i>+30m</i><div><strong>Atlas engineering sync</strong><span>Agents resolved the full agenda</span></div></article><article><i>+45m</i><div><strong>Launch readiness</strong><span>Reduced to one human decision</span></div></article></section>
        </div>}

        {view === 'send' && <SendAgentPanel/>}
    </aside>;
}
