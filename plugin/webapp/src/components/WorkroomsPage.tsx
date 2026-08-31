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

const AGENT_USERNAMES = new Set(['nobs', 'master-agent', 'atlas-agent', 'gemini-enterprise', 'gemini-code-assist', 'github']);

const PROFILES: Record<string, WorkroomProfile> = {
    'agent-workroom-pricing-launch-faq': {stage: 'Pre-work', status: 'Ready for approval', tone: 'planning', summary: 'Turn launch evidence into a customer-safe pricing FAQ.', activity: 'The execution brief is complete. One approval unlocks drafting.', outcome: 'Scope, owners, dependencies and authority are mapped.', progress: 100, agentCount: 5, owner: 'Maya', checks: ['Outcome defined', 'Owners confirmed', 'Dependencies available', 'Authority recorded']},
    'agent-workroom-atlas': {stage: 'Real work', status: 'Decision pending', tone: 'review', summary: 'Close Atlas launch readiness without weakening the security policy.', activity: 'Six agents resolved the evidence. Alex owns the remaining business decision.', outcome: 'Engineering is ready; Calendar action stays locked behind separate approval.', progress: 76, agentCount: 6, owner: 'Alex'},
    'agent-workroom-support-taxonomy': {stage: 'Real work', status: 'Needs human review', tone: 'review', summary: 'Consolidate support tags without breaking reporting history.', activity: 'Agents prepared the migration map; Maya has two label choices to review.', outcome: 'Historical reporting is preserved and the rollback map is ready.', progress: 82, agentCount: 4, owner: 'Maya'},
    'agent-workroom-northstar-onboarding': {stage: 'Real work', status: 'In review', tone: 'active', summary: 'Prepare the Northstar onboarding pack and rollout checklist.', activity: 'The evidence pack is complete and Priya’s Agent is checking launch language.', outcome: 'Owners, dates and controlled-availability language are assembled.', progress: 91, agentCount: 6, owner: 'Priya'},
    'agent-workroom-mobile-release-notes': {stage: 'Real work', status: 'Completed', tone: 'complete', summary: 'Publish accurate mobile release notes from shipped changes.', activity: 'Agents verified every claim against GitHub and Support context.', outcome: 'Nine customer-safe claims shipped with a complete evidence trail.', progress: 100, agentCount: 5, owner: 'Daniel'},
};
const FALLBACK_PROFILE: WorkroomProfile = {stage: 'Pre-work', status: 'Gathering requirements', tone: 'planning', summary: 'The Master Agent is defining the outcome and execution boundary.', activity: 'Requirements and dependency checks are still running.', outcome: 'Waiting for an approval-ready execution brief.', progress: 25, agentCount: 3, owner: 'Unassigned'};

const GROUPS: Array<{id: string; label: string; match: (item: WorkroomProfile) => boolean}> = [
    {id: 'attention', label: 'Waiting on you', match: (item) => item.stage === 'Pre-work'},
    {id: 'running', label: 'In progress', match: (item) => item.stage === 'Real work' && item.tone !== 'complete'},
    {id: 'done', label: 'Completed', match: (item) => item.stage === 'Real work' && item.tone === 'complete'},
];

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
function plainText(value: string, limit: number): string {
    const clean = value.replace(/```[\s\S]*?```/g, ' attached evidence ').replace(/[*_`>#\[\]]/g, '').replace(/\([^)]*\)/g, '').replace(/\s+/g, ' ').trim();
    return clean.length > limit ? `${clean.slice(0, limit - 1)}…` : clean;
}
function relativeTime(value: number): string {
    const minutes = Math.max(0, Math.round((Date.now() - value) / 60000));
    if (minutes < 2) {return 'now';}
    if (minutes < 60) {return `${minutes}m ago`;}
    const hours = Math.round(minutes / 60);
    return hours < 24 ? `${hours}h ago` : `${Math.round(hours / 24)}d ago`;
}
function openChannel(channel: MattermostChannel): void {window.location.assign(channelPath(channel));}

function GeminiMark(): JSX.Element {
    return <svg className='nobs-gemini-mark' viewBox='0 0 64 64' role='img' aria-label='Gemini'>
        <defs>
            <linearGradient id='nobs-gemini-gradient' x1='9' y1='55' x2='55' y2='9' gradientUnits='userSpaceOnUse'>
                <stop offset='0' stopColor='#3186ff'/>
                <stop offset='.46' stopColor='#8e75ff'/>
                <stop offset='1' stopColor='#e45cba'/>
            </linearGradient>
        </defs>
        <path fill='url(#nobs-gemini-gradient)' d='M32 3c2.7 13.9 15.1 26.3 29 29-13.9 2.7-26.3 15.1-29 29C29.3 47.1 16.9 34.7 3 32 16.9 29.3 29.3 16.9 32 3Z'/>
    </svg>;
}

function Avatar({user}: {user?: MattermostUser}): JSX.Element {
    const username = user?.username || '';
    if (username === 'nobs' || username === 'master-agent') {
        return <span className='nobs-agent-avatar is-nobs' aria-hidden='true'><img src={logo} alt=''/></span>;
    }
    if (username === 'gemini-enterprise' || username === 'gemini-code-assist') {
        return <span className='nobs-agent-avatar is-gemini'><GeminiMark/></span>;
    }
    return <span className='nobs-agent-avatar' aria-hidden='true'>{user ? <img src={`/api/v4/users/${encodeURIComponent(user.id)}/image`} alt=''/> : <img src={logo} alt=''/>}</span>;
}

function WorkroomRow({channel, active, onSelect}: {channel: MattermostChannel; active: boolean; onSelect: () => void}): JSX.Element {
    const item = profile(channel);
    return <button type='button' className={`nobs-workroom-row ${active ? 'is-active' : ''}`} onClick={onSelect}>
        <i className={`nobs-workroom-dot is-${item.tone}`} aria-hidden='true'/>
        <span>
            <strong>{title(channel)}</strong>
            <small><em className={`nobs-status nobs-status--${item.tone}`}>{item.status}</em> · {item.agentCount} agents</small>
        </span>
    </button>;
}

function ActivityEntry({item, user}: {item: ActivityItem; user?: MattermostUser}): JSX.Element {
    const agent = Boolean(user && AGENT_USERNAMES.has(user.username)) || item.post.props?.noping_agent === true;
    return <li>
        <Avatar user={user}/>
        <div>
            <header><strong>{displayName(user)}</strong>{agent ? <em>Agent</em> : null}<span>{relativeTime(item.post.create_at)}</span></header>
            <p>{plainText(item.post.message, 260)}</p>
        </div>
    </li>;
}

function CreateWorkroom({working, error, onClose, onCreate}: {
    working: boolean;
    error: string;
    onClose: () => void;
    onCreate: (name: string, goal: string, people: string) => void;
}): JSX.Element {
    const [name, setName] = useState('');
    const [goal, setGoal] = useState('');
    const [people, setPeople] = useState('daniel, priya');

    useEffect(() => {
        const close = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {onClose();}
        };
        window.addEventListener('keydown', close);
        return () => window.removeEventListener('keydown', close);
    }, [onClose]);

    return <div className='nobs-modal-backdrop' role='presentation' onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
        <section className='nobs-workroom-modal' role='dialog' aria-modal='true' aria-labelledby='nobs-workroom-modal-title'>
            <header>
                <div>
                    <h2 id='nobs-workroom-modal-title'>New workroom</h2>
                    <p>The Master Agent gathers requirements, checks dependencies and authority, then asks you to approve the brief before any real work starts.</p>
                </div>
                <button type='button' className='nobs-icon-button' aria-label='Close' onClick={onClose}><i className='icon-close'/></button>
            </header>
            <div className='nobs-workroom-modal__body'>
                <label>
                    <strong>Project</strong>
                    <input value={name} onChange={(event) => setName(event.target.value)} placeholder='Pricing launch FAQ'/>
                </label>
                <label>
                    <strong>What done looks like</strong>
                    <textarea rows={4} value={goal} onChange={(event) => setGoal(event.target.value)} placeholder='Describe the outcome and the constraints that matter.'/>
                </label>
                <label>
                    <strong>People</strong>
                    <input value={people} onChange={(event) => setPeople(event.target.value)} placeholder='daniel, priya'/>
                    <span>Their personal agents join after you approve the scope.</span>
                </label>
            </div>
            {error ? <div className='nobs-inline-error' role='alert'>{error}</div> : null}
            <footer>
                <button type='button' className='nobs-secondary-button' onClick={onClose}>Cancel</button>
                <button type='button' className='nobs-primary-button' disabled={working || !name.trim() || !goal.trim()} onClick={() => onCreate(name, goal, people)}>{working ? 'Starting…' : 'Start pre-work'}</button>
            </footer>
        </section>
    </div>;
}

export function WorkroomsPage(): JSX.Element {
    const [channels, setChannels] = useState<MattermostChannel[]>([]);
    const [posts, setPosts] = useState<Record<string, ActivityItem[]>>({});
    const [users, setUsers] = useState<Record<string, MattermostUser>>({});
    const [teamID, setTeamID] = useState('');
    const [selectedID, setSelectedID] = useState('');
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [mobileDetail, setMobileDetail] = useState(false);
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
        const ordered = GROUPS.flatMap((group) => next.filter((channel) => group.match(profile(channel))));
        setSelectedID((current) => current || ordered[0]?.id || '');
        const pages = await Promise.all(next.map(async (channel) => ({channel, page: await request<MattermostPostPage>(`/api/v4/channels/${encodeURIComponent(channel.id)}/posts?page=0&per_page=100`).catch((): MattermostPostPage => ({order: [], posts: {}}))})));
        const nextPosts: Record<string, ActivityItem[]> = {};
        const userIDs = new Set<string>();
        for (const {channel, page} of pages) {
            nextPosts[channel.id] = page.order.map((postID) => page.posts[postID]).filter((post): post is MattermostPost => Boolean(post && !post.root_id && post.message.trim())).map((post) => ({post, channel}));
            nextPosts[channel.id].forEach(({post}) => userIDs.add(post.user_id));
        }
        setPosts(nextPosts);
        if (userIDs.size) {
            const resolved = await request<MattermostUser[]>('/api/v4/users/ids', {method: 'POST', body: JSON.stringify(Array.from(userIDs))});
            setUsers(Object.fromEntries(resolved.map((user) => [user.id, user])));
        }
    };

    useEffect(() => {
        window.history.replaceState(null, '', `/${teamName()}/nobs/workrooms`);
        document.title = 'Workrooms - NoBS';
        void load().
            catch((caught) => setError(caught instanceof Error ? caught.message : 'Workrooms are temporarily unavailable.')).
            finally(() => setLoading(false));
    }, []);

    const groups = useMemo(() => GROUPS.map((group) => ({...group, items: channels.filter((channel) => group.match(profile(channel)))})).filter((group) => group.items.length), [channels]);
    const selected = channels.find((channel) => channel.id === selectedID) || null;
    const item = selected ? profile(selected) : null;
    const activity = selected ? posts[selected.id] || [] : [];
    const participants = useMemo(() => {
        const seen = new Set<string>();
        return activity.map((entry) => users[entry.post.user_id]).filter((user): user is MattermostUser => {
            if (!user || seen.has(user.id)) {return false;}
            seen.add(user.id);
            return true;
        });
    }, [activity, users]);

    const create = async (name: string, goal: string, people: string) => {
        const usernames = people.split(',').map((entry) => entry.trim().replace(/^@/, '')).filter(Boolean);
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

    return <main className={`nobs-workrooms ${mobileDetail ? 'is-mobile-detail' : ''}`}>
        <header className='nobs-workrooms__header'>
            <div className='nobs-workrooms__identity'>
                <img src={logo} alt=''/>
                <div><strong>Workrooms</strong><span>Projects agents run end to end</span></div>
            </div>
            <button type='button' className='nobs-primary-button' onClick={() => setShowCreate(true)}>New workroom</button>
        </header>
        {error && !showCreate ? <div className='nobs-workrooms__notice' role='alert'>{error}</div> : null}
        <div className='nobs-workrooms__workspace'>
            <aside className='nobs-workrooms__rail' aria-label='Workrooms'>
                <div className='nobs-workrooms__rail-heading'>
                    <strong>Projects</strong>
                    <em>{channels.length}</em>
                </div>
                {loading ? <p className='nobs-workrooms__rail-note'>Loading workrooms…</p> : null}
                {!loading && !channels.length ? <p className='nobs-workrooms__rail-note'>No workrooms yet.</p> : null}
                {groups.map((group) => <section key={group.id} className='nobs-workroom-group'>
                    <h2>{group.label}</h2>
                    {group.items.map((channel) => <WorkroomRow
                        key={channel.id}
                        channel={channel}
                        active={channel.id === selectedID}
                        onSelect={() => {setSelectedID(channel.id); setMobileDetail(true);}}
                    />)}
                </section>)}
            </aside>
            <section className='nobs-workrooms__detail' aria-live='polite'>
                {!selected || !item ? <div className='nobs-workrooms__empty'>
                    <img src={logo} alt=''/>
                    <strong>{loading ? 'Loading workrooms…' : 'Select a workroom'}</strong>
                    <span>Each workroom is one bounded project agents carry from brief to finished work.</span>
                </div> : <>
                    <button type='button' className='nobs-mobile-back' onClick={() => setMobileDetail(false)}>Back to projects</button>
                    <header className='nobs-workroom-hero'>
                        <div>
                            <span className='nobs-workroom-hero__meta'>
                                <em className={`nobs-status nobs-status--${item.tone}`}>{item.status}</em>
                                <i aria-hidden='true'/>
                                {item.stage}
                            </span>
                            <h1>{title(selected)}</h1>
                            <p>{item.summary}</p>
                        </div>
                        <button type='button' className='nobs-primary-button' onClick={() => openChannel(selected)}>
                            {item.stage === 'Pre-work' ? 'Review brief' : 'Open workroom'}
                        </button>
                    </header>
                    {participants.length ? <ul className='nobs-workroom-people' aria-label='Working in this room'>
                        {participants.map((user) => <li key={user.id}><Avatar user={user}/>{displayName(user)}</li>)}
                    </ul> : null}
                    <div className='nobs-workroom-grid'>
                        <div className='nobs-workroom-main'>
                            {item.checks?.length ? <section className='nobs-surface'>
                                <div className='nobs-section-title'><div><strong>Readiness</strong></div><em>Approval unlocks execution</em></div>
                                <ul className='nobs-workroom-checks'>
                                    {item.checks.map((check) => <li key={check}><i className='icon-check' aria-hidden='true'/>{check}</li>)}
                                </ul>
                            </section> : null}
                            <section className='nobs-surface'>
                                <div className='nobs-section-title'>
                                    <div><strong>Activity</strong></div>
                                    <em>{activity.length} visible update{activity.length === 1 ? '' : 's'}</em>
                                </div>
                                {activity.length ? <ol className='nobs-workroom-thread'>
                                    {activity.map((entry) => <ActivityEntry key={entry.post.id} item={entry} user={users[entry.post.user_id]}/>)}
                                </ol> : <p className='nobs-muted'>Agents have not posted in this workroom yet.</p>}
                            </section>
                        </div>
                        <aside className='nobs-workroom-aside'>
                            <section className='nobs-surface'>
                                <div className='nobs-section-title'><div><strong>Progress</strong></div><em>{item.progress}%</em></div>
                                <div className={`nobs-workroom-progress is-${item.tone}`}><span style={{width: `${item.progress}%`}}/></div>
                                <p>{item.activity}</p>
                                <dl className='nobs-workroom-facts'>
                                    <div><dt>Reviewer</dt><dd>{item.owner}</dd></div>
                                    <div><dt>Agents</dt><dd>{item.agentCount}</dd></div>
                                </dl>
                            </section>
                            <section className='nobs-surface'>
                                <div className='nobs-section-title'><div><strong>What done looks like</strong></div></div>
                                <p className='nobs-muted'>{item.outcome}</p>
                            </section>
                        </aside>
                    </div>
                </>}
            </section>
        </div>
        {showCreate ? <CreateWorkroom
            working={working}
            error={error}
            onClose={() => {setShowCreate(false); setError('');}}
            onCreate={(name, goal, people) => void create(name, goal, people)}
        /> : null}
    </main>;
}
