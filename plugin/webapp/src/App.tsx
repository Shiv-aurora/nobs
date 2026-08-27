import React, {useCallback, useEffect, useState} from 'react';

import {api, APIError} from './api/client';
import {AnswerView} from './components/AnswerView';
import {AskBox} from './components/AskBox';
import {AuditPage} from './components/AuditPage';
import {DecisionCard} from './components/DecisionCard';
import {EmptyState} from './components/EmptyState';
import {HomePage} from './components/HomePage';
import {OrganizationPage} from './components/OrganizationPage';
import {RegistryPage} from './components/RegistryPage';
import {SystemPage} from './components/SystemPage';
import {Sidebar, type View} from './components/Sidebar';
import {Topbar} from './components/Topbar';
import type {AuditEvent, BootstrapResponse, Decision, HealthResponse, MetricsResponse, QueryResult, RegistryResponse} from './types/models';

export function App(): JSX.Element {
    const [view, setView] = useState<View>('home');
    const [bootstrap, setBootstrap] = useState<BootstrapResponse | null>(null);
    const [result, setResult] = useState<QueryResult | null>(null);
    const [registry, setRegistry] = useState<RegistryResponse | null>(null);
    const [audit, setAudit] = useState<AuditEvent[]>([]);
    const [health, setHealth] = useState<HealthResponse | null>(null);
    const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [querying, setQuerying] = useState(false);
    const [resetting, setResetting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const refresh = useCallback(async () => {
        setLoading(true);
        try {
            const [nextBootstrap, nextRegistry, nextAudit, nextHealth, nextMetrics] = await Promise.all([api.bootstrap(), api.registry(), api.audit(), api.health(), api.metrics()]);
            setBootstrap(nextBootstrap);
            setRegistry(nextRegistry);
            setAudit(nextAudit);
            setHealth(nextHealth);
            setMetrics(nextMetrics);
            setError(null);
        } catch (caught) {
            setError(caught instanceof APIError ? caught.message : 'NoPing could not load the workspace.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { void refresh(); }, [refresh]);

    useEffect(() => {
        let timer: number | undefined;
        const onUpdate = () => {
            window.clearTimeout(timer);
            timer = window.setTimeout(() => void refresh(), 150);
        };
        window.addEventListener('noping:run-update', onUpdate);
        window.addEventListener('noping:decision-update', onUpdate);
        return () => {
            window.clearTimeout(timer);
            window.removeEventListener('noping:run-update', onUpdate);
            window.removeEventListener('noping:decision-update', onUpdate);
        };
    }, [refresh]);

    const ask = async (text: string) => {
        setQuerying(true);
        try {
            const next = await api.query(text);
            setResult(next);
            setView('ask');
            setError(null);
            await refresh();
        } catch (caught) {
            setError(caught instanceof APIError ? caught.message : 'The query failed.');
        } finally {
            setQuerying(false);
        }
    };

    const resolveDecision = async (decisionID: string, status: string, rationale: string) => {
        try {
            await api.resolveDecision(decisionID, status, rationale);
            setError(null);
            await refresh();
        } catch (caught) {
            const message = caught instanceof APIError ? caught.message : 'The decision could not be saved.';
            setError(message);
            throw caught;
        }
    };

    const reset = async () => {
        setResetting(true);
        try {
            await api.resetDemo();
            setResult(null);
            setView('home');
            await refresh();
        } finally {
            setResetting(false);
        }
    };

    if (loading && !bootstrap) {
        return <div className='np-loading-screen'><span className='np-spinner'/><strong>Mapping your organization</strong><small>Loading identities, projects, policies, and work state</small></div>;
    }
    if (!bootstrap) {
        return <div className='np-loading-screen is-error'><strong>NoPing could not start</strong><small>{error || 'Unknown error'}</small><button type='button' onClick={() => void refresh()}>Retry</button></div>;
    }

    return (
        <div className='np-app'>
            <Sidebar active={view} needsCount={bootstrap.needs_you.length} onNavigate={setView}/>
            <div className='np-main'>
                <Topbar user={bootstrap.current_user} onReset={() => void reset()} resetting={resetting}/>
                <main className='np-content'>
                    {error && <div className='np-error-banner'>{error}</div>}
                    {view === 'home' && <HomePage bootstrap={bootstrap} loading={querying} onAsk={ask} onOpenNeeds={() => setView('needs')} recentResult={result}/>}
                    {view === 'ask' && <div className='np-page np-ask-page'><AskBox compact onSubmit={ask} loading={querying}/>{result ? <AnswerView result={result} onOpenNeeds={() => setView('needs')}/> : <EmptyState title='Ask your company' detail='NoPing will find the right project, team, policy, and people delegates for you.'/>}</div>}
                    {view === 'needs' && <div className='np-page'><div className='np-page-intro'><span>Attention inbox</span><h1>Needs you</h1><p>Only judgment, authority, private knowledge, and unresolved conflicts reach this page.</p></div>{bootstrap.needs_you.length === 0 ? <EmptyState title='Nothing needs you' detail='NoPing handled the routine questions without sending them here.'/> : <div className='np-card-stack'>{bootstrap.needs_you.map((decision: Decision) => <DecisionCard key={decision.id} decision={decision} onResolve={resolveDecision}/>)}</div>}</div>}
                    {view === 'projects' && <OrganizationPage bootstrap={bootstrap} mode='projects'/>}
                    {view === 'people' && <OrganizationPage bootstrap={bootstrap} mode='people'/>}
                    {view === 'registry' && <RegistryPage registry={registry}/>}
                    {view === 'audit' && <AuditPage events={audit}/>}
                    {view === 'system' && <SystemPage health={health} metrics={metrics}/>}
                </main>
            </div>
        </div>
    );
}
