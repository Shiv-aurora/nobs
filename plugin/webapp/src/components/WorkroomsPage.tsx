import React, {useEffect, useMemo, useState} from 'react';

import logo from '../assets/logo.png';

interface MattermostChannel {id: string; team_id: string; name: string; display_name: string; purpose: string; total_msg_count?: number; update_at?: number}
interface MattermostUser {id: string; username: string; first_name?: string; last_name?: string}
interface MattermostPost {id: string; user_id: string; message: string; create_at: number; root_id?: string; props?: Record<string, unknown>}
interface MattermostPostPage {order: string[]; posts: Record<string, MattermostPost>}
type WorkroomStage = 'Pre-work' | 'Real work';
type WorkroomTone = 'planning' | 'active' | 'review' | 'complete';
interface WorkroomProfile {
    stage: WorkroomStage;
    status: string;
    tone: WorkroomTone;
    summary: string;
    activity: string;
    outcome: string;
    progress: number;
    agentCount: number;
    owner: string;
    checks?: string[];
}
interface ActivityItem {post: MattermostPost; channel: MattermostChannel}

const PROFILES: Record<string, WorkroomProfile> = {
    'agent-workroom-pricing-launch-faq': {stage: 'Pre-work', status: 'Ready for approval', tone: 'planning', summary: 'Turn launch evidence into a customer-safe pricing FAQ.', activity: 'The execution brief is complete. One approval unlocks drafting.', outcome: 'Scope, owners, dependencies and authority are mapped.', progress: 100, agentCount: 5, owner: 'Maya', checks: ['Outcome defined', 'Owners confirmed', 'Dependencies available', 'Authority recorded']},
    'agent-workroom-atlas': {stage: 'Real work', status: 'Decision pending', tone: 'review', summary: 'Close Atlas launch readiness without weakening the security policy.', activity: 'Six agents resolved the evidence. Alex owns the remaining business decision.', outcome: 'Engineering is ready; Calendar action stays locked behind separate approval.', progress: 76, agentCount: 6, owner: 'Alex'},
    'agent-workroom-support-taxonomy': {stage: 'Real work', status: 'Needs human review', tone: 'review', summary: 'Consolidate support tags without breaking reporting history.', activity: 'Agents prepared the migration map; Maya has two label choices to review.', outcome: 'Historical reporting is preserved and the rollback map is ready.', progress: 82, agentCount: 4, owner: 'Maya'},
    'agent-workroom-northstar-onboarding': {stage: 'Real work', status: 'In review', tone: 'active', summary: 'Prepare the Northstar onboarding pack and rollout checklist.', activity: 'The evidence pack is complete and Priya’s Agent is checking launch language.', outcome: 'Owners, dates and controlled-availability language are assembled.', progress: 91, agentCount: 6, owner: 'Priya'},
    'agent-workroom-mobile-release-notes': {stage: 'Real work', status: 'Completed', tone: 'complete', summary: 'Publish accurate mobile release notes from shipped changes.', activity: 'Agents verified every claim against GitHub and Support context.', outcome: 'Nine customer-safe claims shipped with a complete evidence trail.', progress: 100, agentCount: 5, owner: 'Daniel'},
};
const FALLBACK_PROFILE: WorkroomProfile = {stage: 'Pre-work', status: 'Gathering requirements', tone: 'planning', summary: 'The Master Agent is defining the outcome and execution boundary.', activity: 'Requirements and dependency checks are still running.', outcome: 'Waiting for an approval-ready execution brief.', progress: 25, agentCount: 3, owner: 'Unassigned'};

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
function displayName(user?: MattermostUser): string {
    if (!user) {return 'Agent';}
    const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim();
    return user.username === 'nobs' ? 'NoBS Agent' : fullName || `@${user.username}`;
}
function plainText(value: string): string {
    const clean = value.replace(/```[\s\S]*?```/g, ' attached evidence ').replace(/[*_`>#\[\]]/g, '').replace(/\([^)]*\)/g, '').replace(/\s+/g, ' ').trim();
    return clean.length > 150 ? `${clean.slice(0, 147)}…` : clean;
}
function relativeTime(value: number): string {
    const minutes = Math.max(0, Math.round((Date.now() - value) / 60000));
    if (minutes < 2) {return 'now';}
    if (minutes < 60) {return `${minutes}m`;}
    const hours = Math.round(minutes / 60);
    return hours < 24 ? `${hours}h` : `${Math.round(hours / 24)}d`;
}
function open(channel: MattermostChannel): void {window.location.assign(channelPath(channel));}

function Avatar({user, small = false}: {user?: MattermostUser; small?: boolean}): JSX.Element {
    return <span className={`nobs-workroom-avatar${small ? ' is-small' : ''}`} title={displayName(user)}>{user ? <img src={`/api/v4/users/${encodeURIComponent(user.id)}/image`} alt=''/> : <img src={logo} alt='NoBS'/>}</span>;
}

function RecentUpdate({item, user}: {item: ActivityItem; user?: MattermostUser}): JSX.Element {
    const agent = user?.username === 'nobs' || item.post.props?.noping_agent === true;
    return <div className='nobs-workroom-update'>
        <Avatar user={user} small/>
        <div><span><strong>{displayName(user)}</strong>{agent ? <em>agent</em> : null}<time>{relativeTime(item.post.create_at)}</time></span><p>{plainText(item.post.message)}</p></div>
    </div>;
}

function WorkroomCard({channel, activity, users}: {channel: MattermostChannel; activity: ActivityItem[]; users: Record<string, MattermostUser>}): JSX.Element {
    const item = profile(channel);
    const recentPeople = Array.from(new Set(activity.map((entry) => entry.post.user_id))).slice(0, 4);
    return <article className={`nobs-workroom-card nobs-workroom-card--${item.tone}`}>
        <button type='button' className='nobs-workroom-card__open' onClick={() => open(channel)} aria-label={`Open ${title(channel)}`}/>
        <div className='nobs-workroom-card__heading'>
            <span className='nobs-workroom-card__icon'><img src={logo} alt=''/></span>
            <div><span className={`nobs-workroom-status nobs-workroom-status--${item.tone}`}><i/>{item.status}</span><strong>{title(channel)}</strong><p>{item.summary}</p></div>
            <i className='icon-chevron-right nobs-workroom-card__chevron' aria-hidden='true'/>
        </div>
        <div className='nobs-workroom-card__now'><span>Working now</span><strong>{item.activity}</strong></div>
        {activity.length ? <div className='nobs-workroom-card__updates'>{activity.slice(0, 2).map((entry) => <RecentUpdate key={entry.post.id} item={entry} user={users[entry.post.user_id]}/>)}</div> : <p className='nobs-workroom-card__activity'>{item.outcome}</p>}
        <div className='nobs-workroom-card__progress-row'><div><span style={{width: `${item.progress}%`}}/></div><strong>{item.progress}%</strong></div>
        <footer>
            <div className='nobs-workroom-people'>{recentPeople.map((userID) => <Avatar key={userID} user={users[userID]}/>)}</div>
            <span>{item.agentCount} agents</span><span>{channel.total_msg_count || 0} updates</span><span>Review: {item.owner}</span>
        </footer>
    </article>;
}

function PreWorkCard({channel}: {channel: MattermostChannel}): JSX.Element {
    const item = profile(channel);
    return <article className='nobs-workroom-attention'>
        <div className='nobs-workroom-attention__copy'><span>YOUR REVIEW UNLOCKS REAL WORK</span><h2>{title(channel)}</h2><p>{item.activity}</p><div className='nobs-workroom-attention__meta'><strong>{item.agentCount} agents ready</strong><i/>No execution started<i/>Authority boundary preserved</div></div>
        <div className='nobs-workroom-checks' aria-label='Pre-work readiness'>{(item.checks || []).map((check) => <span key={check}><i className='icon-check' aria-hidden='true'/>{check}</span>)}</div>
        <button type='button' className='nobs-primary-button' onClick={() => open(channel)}>Review execution brief<i className='icon-chevron-right' aria-hidden='true'/></button>
    </article>;
}

export function WorkroomsPage(): JSX.Element {
    const [channels, setChannels] = useState<MattermostChannel[]>([]);
    const [posts, setPosts] = useState<Record<string, ActivityItem[]>>({});
    const [users, setUsers] = useState<Record<string, MattermostUser>>({});
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
        const available = await request<MattermostChannel[]>(`/api/v4/users/me/teams/${encodeURIComponent(id)}/channels`);
        const next = available.filter((channel) => channel.name.startsWith('agent-workroom-')).sort((a, b) => (b.update_at || 0) - (a.update_at || 0));
        setChannels(next);
        const pages = await Promise.all(next.map(async (channel) => ({channel, page: await request<MattermostPostPage>(`/api/v4/channels/${encodeURIComponent(channel.id)}/posts?page=0&per_page=20`).catch((): MattermostPostPage => ({order: [], posts: {}}))})));
        const nextPosts: Record<string, ActivityItem[]> = {};
        const userIDs = new Set<string>();
        for (const {channel, page} of pages) {
            nextPosts[channel.id] = page.order.map((postID) => page.posts[postID]).filter((post): post is MattermostPost => Boolean(post && !post.root_id && post.message.trim())).slice(0, 5).map((post) => ({post, channel}));
            nextPosts[channel.id].forEach(({post}) => userIDs.add(post.user_id));
        }
        setPosts(nextPosts);
        if (userIDs.size) {
            const resolved = await request<MattermostUser[]>('/api/v4/users/ids', {method: 'POST', body: JSON.stringify(Array.from(userIDs))});
            setUsers(Object.fromEntries(resolved.map((user) => [user.id, user])));
        }
    };
    useEffect(() => {window.history.replaceState(null, '', `/${teamName()}/nobs/workrooms`); document.title = 'Workrooms - NoBS'; void load().catch((caught) => setError(caught instanceof Error ? caught.message : 'Workrooms are temporarily unavailable.'));}, []);

    const usernames = useMemo(() => people.split(',').map((item) => item.trim().replace(/^@/, '')).filter(Boolean), [people]);
    const preWork = channels.filter((channel) => profile(channel).stage === 'Pre-work');
    const realWork = channels.filter((channel) => profile(channel).stage === 'Real work');
    const activity = Object.values(posts).flat().sort((a, b) => b.post.create_at - a.post.create_at);
    const totalUpdates = channels.reduce((sum, channel) => sum + (channel.total_msg_count || 0), 0);
    const needsReview = channels.filter((channel) => ['planning', 'review'].includes(profile(channel).tone)).length;
    const agentSeats = channels.reduce((sum, channel) => sum + profile(channel).agentCount, 0);
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
        <header className='nobs-workrooms__header'><div><img src={logo} alt=''/><span><strong>Workrooms</strong><small>Agents doing bounded work, with evidence and human authority kept visible.</small></span></div><button type='button' className='nobs-primary-button' onClick={() => setShowCreate((value) => !value)}>{showCreate ? 'Close' : 'New project'}</button></header>
        {error ? <div className='nobs-workrooms__error' role='alert'>{error}</div> : null}
        <div className='nobs-workrooms__body'>
            {showCreate ? <section className='nobs-workroom-create'><div><span>NEW AGENT PROJECT</span><h1>Start with Pre-work</h1><p>The Master Agent gathers requirements, checks dependencies and authority, then asks you to approve the execution brief before any Real work begins.</p></div><label><strong>Project</strong><input value={name} onChange={(event) => setName(event.target.value)} placeholder='e.g. Pricing launch FAQ'/></label><label><strong>Desired outcome</strong><textarea rows={4} value={goal} onChange={(event) => setGoal(event.target.value)} placeholder='Describe what done looks like and the constraints that matter.'/></label><label><strong>People</strong><input value={people} onChange={(event) => setPeople(event.target.value)} placeholder='daniel, priya'/><small>Their personal agents join after scope approval.</small></label><button type='button' className='nobs-primary-button' disabled={working || !name.trim() || !goal.trim()} onClick={() => void create()}>{working ? 'Starting Pre-work…' : 'Create Pre-work room'}</button></section> : null}
            <section className='nobs-workroom-summary' aria-label='Workroom summary'>
                <div><span>WORKROOMS</span><strong>{channels.length}</strong><small>bounded projects</small></div>
                <div><span>AGENT ACTIVITY</span><strong>{totalUpdates}</strong><small>auditable updates</small></div>
                <div><span>COLLABORATION</span><strong>{agentSeats}</strong><small>agent assignments</small></div>
                <div className={needsReview ? 'is-attention' : ''}><span>HUMAN INPUT</span><strong>{needsReview}</strong><small>focused reviews</small></div>
            </section>
            {preWork.length ? <section className='nobs-workrooms__list' aria-label='Needs your attention'><div className='nobs-workrooms__section-title'><div><strong>Needs your attention</strong><span>Agents finished the preparation; a human boundary is next.</span></div><em>{preWork.length} ready</em></div>{preWork.map((channel) => <PreWorkCard key={channel.id} channel={channel}/>)}</section> : null}
            <section className='nobs-workrooms__workspace'>
                <div className='nobs-workrooms__list' aria-label='Agent project execution'><div className='nobs-workrooms__section-title'><div><strong>Agent project execution</strong><span>Open a room to inspect the full multi-agent conversation and evidence.</span></div><em>{realWork.length} projects</em></div><div className='nobs-workroom-grid'>{realWork.map((channel) => <WorkroomCard key={channel.id} channel={channel} activity={posts[channel.id] || []} users={users}/>)}</div>{!channels.length ? <div className='nobs-workrooms__empty'><img src={logo} alt=''/><strong>No workrooms yet</strong><span>Create a bounded project and let the Master Agent prepare it for execution.</span></div> : null}</div>
                <aside className='nobs-workroom-feed' aria-label='Live agent activity'><header><div><i/><span><strong>Live agent activity</strong><small>Across every workroom</small></span></div><em>{activity.length ? 'Live' : 'Waiting'}</em></header><div>{activity.slice(0, 7).map((entry) => <button type='button' key={entry.post.id} onClick={() => open(entry.channel)}><RecentUpdate item={entry} user={users[entry.post.user_id]}/><span>{title(entry.channel)}<i className='icon-chevron-right' aria-hidden='true'/></span></button>)}</div><footer><span>Every update stays in its native Mattermost conversation.</span></footer></aside>
            </section>
        </div>
    </main>;
}
