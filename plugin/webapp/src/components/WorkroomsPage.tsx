import React, {useEffect, useMemo, useState} from 'react';

import logo from '../assets/logo.png';

interface MattermostChannel {
    id: string;
    team_id: string;
    name: string;
    display_name: string;
    purpose: string;
    total_msg_count?: number;
    update_at?: number;
}

interface MattermostUser {
    id: string;
    username: string;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(path, {
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest', ...(options?.headers || {})},
        ...options,
    });
    const body = await response.json().catch(() => ({message: response.statusText}));
    if (!response.ok) {
        throw new Error(typeof body.message === 'string' ? body.message : 'The workroom request failed.');
    }
    return body as T;
}

function slug(value: string): string {
    return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 42);
}

function teamName(): string {
    return window.location.pathname.split('/').filter(Boolean)[0] || 'acme';
}

function channelPath(channel: MattermostChannel): string {
    return `/${teamName()}/channels/${channel.name}`;
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
        if (!id) {
            setChannels([]);
            return;
        }
        const next = await request<MattermostChannel[]>(`/api/v4/users/me/teams/${encodeURIComponent(id)}/channels`);
        setChannels(next.filter((channel) => channel.name.startsWith('agent-workroom-')).sort((a, b) => (b.update_at || 0) - (a.update_at || 0)));
    };

    useEffect(() => {
        window.history.replaceState(null, '', `/${teamName()}/nobs/workrooms`);
        document.title = 'Workrooms - NoBS';
        void load().catch((caught) => setError(caught instanceof Error ? caught.message : 'Workrooms are temporarily unavailable.'));
    }, []);

    const usernames = useMemo(() => people.split(',').map((item) => item.trim().replace(/^@/, '')).filter(Boolean), [people]);

    const create = async () => {
        if (!teamID || !name.trim() || !goal.trim()) {
            return;
        }
        setWorking(true);
        setError('');
        try {
            const channel = await request<MattermostChannel>('/api/v4/channels', {
                method: 'POST',
                body: JSON.stringify({
                    team_id: teamID,
                    name: `agent-workroom-${slug(name)}-${Date.now().toString().slice(-5)}`,
                    display_name: `Agent Workroom · ${name.trim()}`,
                    purpose: goal.trim(),
                    type: 'P',
                }),
            });
            const members = await Promise.all(usernames.map((username) => request<MattermostUser>(`/api/v4/users/username/${encodeURIComponent(username)}`).catch(() => null)));
            await Promise.all(members.filter((user): user is MattermostUser => Boolean(user)).map((user) => request(`/api/v4/channels/${encodeURIComponent(channel.id)}/members`, {method: 'POST', body: JSON.stringify({user_id: user.id})}).catch(() => undefined)));
            await request('/api/v4/posts', {
                method: 'POST',
                body: JSON.stringify({
                    channel_id: channel.id,
                    message: `@nobs Start a project workroom for **${name.trim()}**.\n\nGoal: ${goal.trim()}\n\nTeam: ${usernames.length ? usernames.map((username) => `@${username}`).join(', ') : 'my agent and me'}\n\nBuild a concise first-pass plan, identify the first evidence to gather, and route the opening task to the right delegate.`,
                }),
            });
            window.location.assign(channelPath(channel));
        } catch (caught) {
            setError(caught instanceof Error ? caught.message : 'The workroom could not be created.');
            setWorking(false);
        }
    };

    return <main className='nobs-workrooms'>
        <header className='nobs-workrooms__header'>
            <div><img src={logo} alt=''/><span><strong>Agent Workrooms</strong><small>Give a small project to the right people and let their agents coordinate it.</small></span></div>
            <button type='button' className='nobs-primary-button' onClick={() => setShowCreate((value) => !value)}>{showCreate ? 'Close' : 'New project'}</button>
        </header>
        {error ? <div className='nobs-workrooms__error' role='alert'>{error}</div> : null}
        <div className='nobs-workrooms__body'>
            {showCreate ? <section className='nobs-workroom-create'>
                <div><span>NEW AGENT PROJECT</span><h1>What should the agents move forward?</h1><p>NoBS creates a private native workroom, adds your teammates, and asks Gemini to route the opening work.</p></div>
                <label><strong>Project</strong><input value={name} onChange={(event) => setName(event.target.value)} placeholder='e.g. Atlas onboarding polish'/></label>
                <label><strong>Outcome</strong><textarea rows={4} value={goal} onChange={(event) => setGoal(event.target.value)} placeholder='Describe what done looks like and any constraint that matters.'/></label>
                <label><strong>People</strong><input value={people} onChange={(event) => setPeople(event.target.value)} placeholder='daniel, priya'/><small>Comma-separated NoBS usernames. Their personal agents join the work.</small></label>
                <button type='button' className='nobs-primary-button' disabled={working || !name.trim() || !goal.trim()} onClick={() => void create()}>{working ? 'Engaging agents…' : 'Create workroom and engage agents'}</button>
            </section> : null}

            <section className='nobs-workrooms__list' aria-label='Project workrooms'>
                <div className='nobs-workrooms__section-title'><div><strong>Active projects</strong><span>{channels.length} workroom{channels.length === 1 ? '' : 's'}</span></div><em>Native private channels</em></div>
                <div className='nobs-workroom-grid'>{channels.map((channel) => <button type='button' key={channel.id} onClick={() => window.location.assign(channelPath(channel))}>
                    <span className='nobs-workroom-grid__icon'><img src={logo} alt=''/></span>
                    <span><strong>{channel.display_name.replace(/^Agent Workroom · /, '')}</strong><small>{channel.purpose || 'Agents are coordinating this project.'}</small></span>
                    <em>{channel.total_msg_count || 0} messages</em>
                    <i className='icon-chevron-right' aria-hidden='true'/>
                </button>)}</div>
                {!channels.length ? <div className='nobs-workrooms__empty'><img src={logo} alt=''/><strong>No workrooms yet</strong><span>Create a bounded project and let the relevant personal agents start the work.</span></div> : null}
            </section>
        </div>
    </main>;
}
