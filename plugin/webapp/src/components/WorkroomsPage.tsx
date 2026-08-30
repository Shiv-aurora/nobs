import React, {useEffect, useMemo, useState} from 'react';

import logo from '../assets/logo.png';

interface MattermostChannel {id: string; team_id: string; name: string; display_name: string; purpose: string; total_msg_count?: number; update_at?: number}
interface MattermostUser {id: string; username: string}
type WorkroomStage = 'Pre-work' | 'Real work';
type WorkroomTone = 'planning' | 'active' | 'review' | 'complete';
interface WorkroomProfile {stage: WorkroomStage; status: string; tone: WorkroomTone; summary: string; activity: string; progress: number; agentCount: number; checks?: string[]}

const PROFILES: Record<string, WorkroomProfile> = {
    'agent-workroom-pricing-launch-faq': {stage: 'Pre-work', status: 'Ready for approval', tone: 'planning', summary: 'Turn launch evidence into a customer-safe pricing FAQ.', activity: 'Master Agent mapped the outcome, owners, evidence and one remaining approval.', progress: 100, agentCount: 5, checks: ['Outcome defined', 'Owners confirmed', 'Dependencies available', 'Authority boundary recorded']},
    'agent-workroom-support-taxonomy': {stage: 'Real work', status: 'Needs human review', tone: 'review', summary: 'Consolidate support tags without breaking reporting history.', activity: 'Agents prepared the migration map; Maya needs to approve two customer-facing labels.', progress: 82, agentCount: 4},
    'agent-workroom-northstar-onboarding': {stage: 'Real work', status: 'In review', tone: 'active', summary: 'Prepare the Northstar onboarding pack and rollout checklist.', activity: 'The evidence pack is complete and Priya’s Agent is reviewing launch language.', progress: 91, agentCount: 6},
    'agent-workroom-mobile-release-notes': {stage: 'Real work', status: 'Completed', tone: 'complete', summary: 'Publish accurate mobile release notes from shipped changes.', activity: 'Release notes were verified against GitHub and shared with Customer Support.', progress: 100, agentCount: 5},
};
const FALLBACK_PROFILE: WorkroomProfile = {stage: 'Pre-work', status: 'Gathering requirements', tone: 'planning', summary: 'The Master Agent is defining the outcome and execution boundary.', activity: 'Waiting for the first requirements and dependency check.', progress: 25, agentCount: 3};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(path, {credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest', ...(options?.headers || {})}, ...options});
    const body = await response.json().catch(() => ({message: response.statusText}));
    if (!response.ok) {throw new Error(typeof body.message === 'string' ? body.message : 'The workroom request failed.');}
    return body as T;
}
function slug(value: string): string {return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 42);}
function teamName(): string {return window.location.pathname.split('/').filter(Boolean)[0] || 'acme';}
function channelPath(channel: MattermostChannel): string {return `/${teamName()}/channels/${channel.name}`;}
function title(channel: MattermostChannel): string {return channel.display_name.replace(/^Agent Workroom · /, '');}
function profile(channel: MattermostChannel): WorkroomProfile {return PROFILES[channel.name] || {...FALLBACK_PROFILE, summary: channel.purpose || FALLBACK_PROFILE.summary};}

function WorkroomCard({channel}: {channel: MattermostChannel}): JSX.Element {
    const item = profile(channel);
    return <article className={`nobs-workroom-card nobs-workroom-card--${item.tone}`}>
        <div className='nobs-workroom-card__top'><span className='nobs-workroom-card__icon'><img src={logo} alt=''/></span><span className={`nobs-workroom-status nobs-workroom-status--${item.tone}`}>{item.status}</span></div>
        <div className='nobs-workroom-card__copy'><strong>{title(channel)}</strong><p>{item.summary}</p></div>
        {item.checks ? <div className='nobs-workroom-checks' aria-label='Pre-work readiness'>{item.checks.map((check) => <span key={check}><i className='icon-check' aria-hidden='true'/>{check}</span>)}</div> : <p className='nobs-workroom-card__activity'>{item.activity}</p>}
        <div className='nobs-workroom-progress' aria-label={`${item.progress}% complete`}><span style={{width: `${item.progress}%`}}/></div>
        <footer><span>{item.agentCount} agents · {channel.total_msg_count || 0} updates</span><button type='button' onClick={() => window.location.assign(channelPath(channel))}>{item.stage === 'Pre-work' ? 'Review pre-work' : 'Open workroom'}<i className='icon-chevron-right' aria-hidden='true'/></button></footer>
    </article>;
}

export function WorkroomsPage(): JSX.Element {
    const [channels, setChannels] = useState<MattermostChannel[]>([]);
    const [teamID, setTeamID] = useState('');
    const [showCreate, setShowCreate] = useState(false);
    const [name, setName] = useState('');
    const [goal, setGoal] = useState('');
    const [people, setPeople] = useState('daniel, priya');
    const [working, setWorking] = useState(false);
    const [error, setError] = useState('');

    const load = async () => {
        const teams = await request<Array<{id: string}>>('/api/v4/users/me/teams');
        const id = teams[0]?.id || '';
        setTeamID(id);
        if (!id) {setChannels([]); return;}
        const next = await request<MattermostChannel[]>(`/api/v4/users/me/teams/${encodeURIComponent(id)}/channels`);
        setChannels(next.filter((channel) => channel.name.startsWith('agent-workroom-') && channel.name !== 'agent-workroom-atlas').sort((a, b) => (b.update_at || 0) - (a.update_at || 0)));
    };
    useEffect(() => {window.history.replaceState(null, '', `/${teamName()}/nobs/workrooms`); document.title = 'Workrooms - NoBS'; void load().catch((caught) => setError(caught instanceof Error ? caught.message : 'Workrooms are temporarily unavailable.'));}, []);

    const usernames = useMemo(() => people.split(',').map((item) => item.trim().replace(/^@/, '')).filter(Boolean), [people]);
    const preWork = channels.filter((channel) => profile(channel).stage === 'Pre-work');
    const realWork = channels.filter((channel) => profile(channel).stage === 'Real work');
    const create = async () => {
        if (!teamID || !name.trim() || !goal.trim()) {return;}
        setWorking(true); setError('');
        try {
            const channel = await request<MattermostChannel>('/api/v4/channels', {method: 'POST', body: JSON.stringify({team_id: teamID, name: `agent-workroom-${slug(name)}-${Date.now().toString().slice(-5)}`, display_name: `Agent Workroom · ${name.trim()}`, purpose: goal.trim(), type: 'P'})});
            const members = await Promise.all(usernames.map((username) => request<MattermostUser>(`/api/v4/users/username/${encodeURIComponent(username)}`).catch(() => null)));
            await Promise.all(members.filter((user): user is MattermostUser => Boolean(user)).map((user) => request(`/api/v4/channels/${encodeURIComponent(channel.id)}/members`, {method: 'POST', body: JSON.stringify({user_id: user.id})}).catch(() => undefined)));
            await request('/api/v4/posts', {method: 'POST', body: JSON.stringify({channel_id: channel.id, message: `@nobs Start **Pre-work** for **${name.trim()}**.\n\nDesired outcome: ${goal.trim()}\n\nTeam: ${usernames.length ? usernames.map((username) => `@${username}`).join(', ') : 'my agent and me'}\n\nAs Master Agent, clarify the product requirements, verify dependencies and permissions, identify missing human decisions, and return one approval-ready execution brief. Do not begin Real work until the brief is approved.`})});
            window.location.assign(channelPath(channel));
        } catch (caught) {setError(caught instanceof Error ? caught.message : 'The workroom could not be created.'); setWorking(false);}
    };

    return <main className='nobs-workrooms'>
        <header className='nobs-workrooms__header'><div><img src={logo} alt=''/><span><strong>Workrooms</strong><small>Small projects your agents can move forward without another meeting.</small></span></div><button type='button' className='nobs-primary-button' onClick={() => setShowCreate((value) => !value)}>{showCreate ? 'Close' : 'New project'}</button></header>
        {error ? <div className='nobs-workrooms__error' role='alert'>{error}</div> : null}
        <div className='nobs-workrooms__body'>
            {showCreate ? <section className='nobs-workroom-create'><div><span>NEW AGENT PROJECT</span><h1>Start with Pre-work</h1><p>The Master Agent gathers requirements, checks dependencies and authority, then asks you to approve the execution brief before any Real work begins.</p></div><label><strong>Project</strong><input value={name} onChange={(event) => setName(event.target.value)} placeholder='e.g. Pricing launch FAQ'/></label><label><strong>Desired outcome</strong><textarea rows={4} value={goal} onChange={(event) => setGoal(event.target.value)} placeholder='Describe what done looks like and the constraints that matter.'/></label><label><strong>People</strong><input value={people} onChange={(event) => setPeople(event.target.value)} placeholder='daniel, priya'/><small>Their personal agents join after scope approval.</small></label><button type='button' className='nobs-primary-button' disabled={working || !name.trim() || !goal.trim()} onClick={() => void create()}>{working ? 'Starting Pre-work…' : 'Create Pre-work room'}</button></section> : null}
            <section className='nobs-workrooms__list' aria-label='Pre-work projects'><div className='nobs-workrooms__section-title'><div><strong>Pre-work</strong><span>Requirements, dependencies and execution approval</span></div><em>{preWork.length} waiting</em></div><div className='nobs-workroom-grid nobs-workroom-grid--prework'>{preWork.map((channel) => <WorkroomCard key={channel.id} channel={channel}/>)}</div></section>
            <section className='nobs-workrooms__list' aria-label='Real work projects'><div className='nobs-workrooms__section-title'><div><strong>Real work</strong><span>Approved projects actively coordinated by agents</span></div><em>{realWork.length} projects</em></div><div className='nobs-workroom-grid'>{realWork.map((channel) => <WorkroomCard key={channel.id} channel={channel}/>)}</div>{!channels.length ? <div className='nobs-workrooms__empty'><img src={logo} alt=''/><strong>No workrooms yet</strong><span>Create a bounded project and let the Master Agent prepare it for execution.</span></div> : null}</section>
        </div>
    </main>;
}
