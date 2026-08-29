import React, {useEffect, useMemo, useState} from 'react';

import {api, APIError} from '../api/client';
import logo from '../assets/logo.png';
import type {Meeting, MeetingDetail} from '../types/models';

const GEMINI_ENTERPRISE_ICON = 'https://avatars.slack-edge.com/2025-09-17/9549827723233_9cb3f87dee7d9088b89b_512.png';
const DEMO_USERNAMES = ['shivam', 'maya', 'daniel', 'sarah', 'priya', 'alex'];

interface ChannelOption {
    id: string;
    display_name: string;
    name: string;
    type: string;
}

function dateLabel(value: string): string {
    return new Intl.DateTimeFormat(undefined, {weekday: 'long', month: 'short', day: 'numeric'}).format(new Date(value));
}

function timeLabel(value: string): string {
    return new Intl.DateTimeFormat(undefined, {hour: 'numeric', minute: '2-digit'}).format(new Date(value));
}

function durationLabel(meeting: Meeting): string {
    const minutes = Math.round((new Date(meeting.end_at).getTime() - new Date(meeting.start_at).getTime()) / 60000);
    return `${minutes} min`;
}

function meetingPath(): string {
    const teamName = window.location.pathname.split('/').filter(Boolean)[0] || 'acme';
    return `/${teamName}/nobs/calendar`;
}

async function loadChannels(): Promise<ChannelOption[]> {
    const teams = await fetch('/api/v4/users/me/teams', {credentials: 'same-origin'}).then((response) => response.ok ? response.json() as Promise<Array<{id: string}>> : []);
    if (!teams.length) {
        return [];
    }
    return fetch(`/api/v4/users/me/teams/${encodeURIComponent(teams[0].id)}/channels`, {credentials: 'same-origin'}).then((response) => response.ok ? response.json() as Promise<ChannelOption[]> : []);
}

async function loadUserAvatars(): Promise<Record<string, string>> {
    const entries = await Promise.all(DEMO_USERNAMES.map(async (username) => {
        const response = await fetch(`/api/v4/users/username/${encodeURIComponent(username)}`, {credentials: 'same-origin'});
        if (!response.ok) {
            return [username, ''] as const;
        }
        const user = await response.json() as {id: string};
        return [username, `/api/v4/users/${encodeURIComponent(user.id)}/image`] as const;
    }));
    return Object.fromEntries(entries.filter(([, url]) => Boolean(url)));
}

function agentUsername(agentName: string): string {
    return agentName.split(/[\s']/)[0].toLowerCase();
}

function AgentAvatar({name, kind, avatars}: {name: string; kind: string; avatars: Record<string, string>}): JSX.Element {
    if (name === 'GitHub') {
        return <div className='nobs-agent-avatar is-github' aria-label='GitHub'><i className='icon-github'/></div>;
    }
    if (kind === 'project' && name.includes('Atlas')) {
        return <div className='nobs-agent-avatar is-atlas' aria-label='Project Atlas'><i className='icon-rocket-launch-outline'/></div>;
    }
    if (kind === 'integration' && name.includes('Gemini')) {
        return <div className='nobs-agent-avatar is-integration'><img src={GEMINI_ENTERPRISE_ICON} alt='Gemini'/></div>;
    }
    const avatar = avatars[agentUsername(name)];
    return <div className={`nobs-agent-avatar is-${kind}`}>{avatar ? <img src={avatar} alt={name}/> : name.split(' ').map((part) => part[0]).slice(0, 2).join('')}</div>;
}

function turnTime(value: string): string {
    return new Intl.DateTimeFormat(undefined, {hour: 'numeric', minute: '2-digit'}).format(new Date(value));
}

export function CalendarPage(): JSX.Element {
    const [meetings, setMeetings] = useState<Meeting[]>([]);
    const [selectedID, setSelectedID] = useState('');
    const [detail, setDetail] = useState<MeetingDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [working, setWorking] = useState(false);
    const [error, setError] = useState('');
    const [channels, setChannels] = useState<ChannelOption[]>([]);
    const [shareChannelID, setShareChannelID] = useState('');
    const [mobileDetail, setMobileDetail] = useState(false);
    const [userAvatars, setUserAvatars] = useState<Record<string, string>>({});

    const refreshList = async (keepSelection = true) => {
        const next = await api.meetings();
        setMeetings(next);
        const candidate = keepSelection && selectedID ? selectedID : next.find((item) => item.preparation_eligibility === 'eligible')?.id || next[0]?.id || '';
        setSelectedID(candidate);
        return candidate;
    };

    const refreshDetail = async (meetingID: string) => {
        if (!meetingID) {
            setDetail(null);
            return;
        }
        setDetail(await api.meeting(meetingID));
    };

    useEffect(() => {
        const teamName = window.location.pathname.split('/').filter(Boolean)[0] || 'acme';
        window.history.replaceState(null, '', `/${teamName}/nobs/calendar`);
        document.title = 'Calendar - NoBS';
        Promise.all([refreshList(false), loadChannels(), loadUserAvatars()]).then(async ([meetingID, nextChannels, avatars]) => {
            setChannels(nextChannels);
            setUserAvatars(avatars);
            const project = nextChannels.find((channel) => channel.name === 'project-atlas');
            setShareChannelID(project?.id || nextChannels[0]?.id || '');
            await refreshDetail(meetingID);
            setError('');
        }).catch((caught) => setError(caught instanceof APIError ? caught.message : 'Calendar is temporarily unavailable.')).finally(() => setLoading(false));
    }, []);

    const selectMeeting = async (meetingID: string) => {
        setSelectedID(meetingID);
        setMobileDetail(true);
        setWorking(true);
        try {
            await refreshDetail(meetingID);
            setError('');
        } catch (caught) {
            setError(caught instanceof APIError ? caught.message : 'This meeting could not be opened.');
        } finally {
            setWorking(false);
        }
    };

    const prepare = async () => {
        if (!detail) {
            return;
        }
        setWorking(true);
        try {
            await api.prepareMeeting(detail.meeting.id);
            await refreshList();
            await refreshDetail(detail.meeting.id);
            setError('');
        } catch (caught) {
            setError(caught instanceof APIError ? caught.message : 'The agents could not prepare this meeting.');
        } finally {
            setWorking(false);
        }
    };

    const confirm = async (action: 'cancel' | 'shorten') => {
        if (!detail) {
            return;
        }
        setWorking(true);
        try {
            await api.confirmMeetingAction(detail.meeting.id, action, detail.meeting.etag, action === 'shorten' ? 15 : undefined);
            await refreshList();
            await refreshDetail(detail.meeting.id);
            setError('');
        } catch (caught) {
            setError(caught instanceof APIError ? caught.message : 'The Calendar change was not applied.');
        } finally {
            setWorking(false);
        }
    };

    const share = async () => {
        if (!detail || !shareChannelID) {
            return;
        }
        setWorking(true);
        try {
            await api.shareMeeting(detail.meeting.id, shareChannelID);
            setError('Brief shared to the selected conversation.');
        } catch (caught) {
            setError(caught instanceof APIError ? caught.message : 'The meeting brief could not be shared.');
        } finally {
            setWorking(false);
        }
    };

    const grouped = useMemo(() => meetings.reduce<Record<string, Meeting[]>>((groups, meeting) => {
        const day = dateLabel(meeting.start_at);
        groups[day] = [...(groups[day] || []), meeting];
        return groups;
    }, {}), [meetings]);

    const selected = detail?.meeting;
    const brief = detail?.run?.brief;

    return <main className={`nobs-calendar ${mobileDetail ? 'is-mobile-detail' : ''}`}>
        <header className='nobs-calendar__header'>
            <div className='nobs-calendar__identity'><i className='icon-calendar-outline' aria-hidden='true'/><div><strong>Calendar</strong><span>Meeting preparation and decisions</span></div></div>
            <button type='button' className='nobs-secondary-button' onClick={() => void refreshList().then(refreshDetail)}><i className='icon-refresh' aria-hidden='true'/> Refresh</button>
        </header>
        {error && <div className={`nobs-calendar__notice ${error.startsWith('Brief shared') ? 'is-success' : ''}`}>{error}</div>}
        <div className='nobs-calendar__workspace'>
            <aside className='nobs-calendar__agenda' aria-label='Upcoming meetings'>
                <div className='nobs-calendar__agenda-heading'><div><strong>Meetings</strong><span>Upcoming</span></div><em>{meetings.length}</em></div>
                {loading ? <div className='nobs-calendar__loading'>Loading your calendar…</div> : Object.entries(grouped).map(([day, items]) => <section key={day} className='nobs-day-group'>
                    <h2>{day}</h2>
                    {items.map((meeting) => <button type='button' key={meeting.id} className={`nobs-meeting-row ${selectedID === meeting.id ? 'is-active' : ''}`} onClick={() => void selectMeeting(meeting.id)}>
                        <time>{timeLabel(meeting.start_at)}</time>
                        <span><strong>{meeting.title}</strong><small>{durationLabel(meeting)} · {meeting.attendees.length} attendees</small></span>
                        <em className={`nobs-status nobs-status--${meeting.preparation_status}`}>{meeting.preparation_status === 'not_started' ? 'Ready to prepare' : meeting.preparation_status}</em>
                    </button>)}
                </section>)}
            </aside>
            <section className='nobs-calendar__detail' aria-live='polite'>
                {!selected || loading ? <div className='nobs-calendar__empty'><img src={logo} alt=''/><strong>Select a meeting</strong><span>NoBS will show what agents can resolve before humans join.</span></div> : <>
                    <button type='button' className='nobs-mobile-back' onClick={() => setMobileDetail(false)}>Back to agenda</button>
                    <header className='nobs-meeting-hero'>
                        <div><span>{dateLabel(selected.start_at)} · {timeLabel(selected.start_at)}–{timeLabel(selected.end_at)}</span><h1>{selected.title}</h1><p>{selected.description}</p></div>
                        <div className='nobs-meeting-hero__actions'>
                            {selected.preparation_eligibility === 'eligible' && !detail?.run && <button type='button' className='nobs-primary-button' disabled={working} onClick={() => void prepare()}>{working ? 'Agents preparing…' : 'Prepare meeting'}</button>}
                            {selected.preparation_eligibility === 'skipped' && <span className='nobs-human-badge'>Human meeting · agents skipped</span>}
                            {detail?.run && <span className='nobs-prepared-badge'>Prepared by {new Set(detail.run.turns.map((turn) => turn.agent_name)).size} agents</span>}
                        </div>
                    </header>
                    <section className='nobs-attendee-strip' aria-label='Attendees'>{selected.attendees.map((attendee) => <article key={attendee.user_id}><span>{userAvatars[attendee.user_id] ? <img src={userAvatars[attendee.user_id]} alt=''/> : attendee.name.split(' ').map((part) => part[0]).join('')}</span><div><strong>{attendee.name}</strong><small>{attendee.role} · delegate ready</small></div></article>)}</section>
                    <div className='nobs-meeting-grid'>
                        <div className='nobs-meeting-main'>
                            {brief && <section className='nobs-brief-hero'>
                                <div><span>Time saved</span><strong>{brief.original_duration_minutes} → {brief.recommended_duration_minutes} min</strong><p>{brief.summary}</p></div>
                                <div><strong>{brief.minutes_saved}</strong><span>minutes returned</span></div>
                            </section>}
                            {detail?.run && <section className='nobs-surface'>
                                <div className='nobs-section-title'><div><strong>Related work</strong><span>Completed before the meeting</span></div></div>
                                <div className='nobs-work-actions'>{detail.run.work_actions.map((action) => <article key={action.id}><header><span className='nobs-provider'>{action.provider === 'GitHub' ? <i className='icon-github' aria-hidden='true'/> : null}{action.provider}</span><em>{action.status}</em></header><strong>{action.title}</strong><p>{action.summary}</p>{action.source_url && <a href={action.source_url} target='_blank' rel='noreferrer'>Open evidence</a>}</article>)}</div>
                            </section>}
                            {detail?.run?.security_findings.length ? <section className='nobs-security-card'><span>Security boundary enforced</span><strong>Untrusted content quarantined</strong><p>{detail.run.security_findings[0].reason}</p></section> : null}
                            {brief && <section className='nobs-surface nobs-disposition'>
                                <span>Recommendation</span><strong>{brief.recommended_disposition === 'cancel' ? 'Cancel this meeting' : brief.recommended_disposition === 'shorten' ? 'Shorten to 15 minutes' : 'Keep this meeting'}</strong>
                                <p>Calendar changes require the organizer's confirmation.</p>
                                {selected.confirmed_action === 'none' ? <button type='button' className='nobs-primary-button' disabled={working} onClick={() => void confirm(brief.recommended_disposition === 'cancel' ? 'cancel' : 'shorten')}>{brief.recommended_disposition === 'cancel' ? 'Confirm cancellation' : 'Confirm 15-minute agenda'}</button> : <div className='nobs-confirmed'>Confirmed · {selected.confirmed_action}</div>}
                            </section>}
                            {brief && <section className='nobs-surface nobs-share-card'><span>Share brief</span><select aria-label='Share meeting brief to' value={shareChannelID} onChange={(event) => setShareChannelID(event.target.value)}>{channels.filter((channel) => channel.type !== 'D').map((channel) => <option key={channel.id} value={channel.id}>{channel.display_name}</option>)}</select><button type='button' className='nobs-secondary-button' disabled={working || !shareChannelID} onClick={() => void share()}>Share to channel</button></section>}
                        </div>
                        <aside className='nobs-meeting-aside'>
                            <section className='nobs-surface nobs-meeting-brief'>
                                <div className='nobs-section-title'><div><strong>Meeting brief</strong><span>Agenda and unresolved decisions</span></div>{brief && <em>{brief.humans_required} human decision{brief.humans_required === 1 ? '' : 's'}</em>}</div>
                                <div className='nobs-agenda-list'>{selected.agenda.length ? selected.agenda.map((item) => <article key={item.id} className={`is-${item.status}`}><span className='nobs-agenda-state'>{item.status === 'resolved' ? 'Done' : item.status === 'needs_human' ? 'Needs judgment' : 'Open'}</span><div><strong>{item.title}</strong>{item.resolution && <p>{item.resolution}</p>}{item.evidence_ids.length > 0 && <small>{item.evidence_ids.length} evidence source{item.evidence_ids.length === 1 ? '' : 's'}</small>}</div></article>) : <p className='nobs-muted'>{selected.preparation_reason}</p>}</div>
                            </section>
                        </aside>
                        {detail?.run && <section className='nobs-surface nobs-preparation'>
                            <div className='nobs-section-title'><div><strong>Agent meeting</strong><span>Attendee agents worked for 15 minutes before the human meeting</span></div><em>{detail.run.turns.length} messages · {new Set(detail.run.turns.map((turn) => turn.agent_name)).size} agents</em></div>
                            <div className='nobs-swarm-presence'>{Array.from(new Set(detail.run.turns.map((turn) => `${turn.agent_name}|${turn.agent_kind}`))).map((agent) => {
                                const [name, kind] = agent.split('|');
                                return <span key={agent}><AgentAvatar name={name} kind={kind} avatars={userAvatars}/>{name}</span>;
                            })}</div>
                            <ol className='nobs-swarm'>{detail.run.turns.map((turn) => <li key={turn.id}>
                                <AgentAvatar name={turn.agent_name} kind={turn.agent_kind} avatars={userAvatars}/>
                                <div><header><strong>{turn.agent_name}</strong><span>{turnTime(turn.created_at)} · {turn.phase.replace('_', ' ')}</span></header><p>{turn.conclusion}</p>{turn.open_question && <blockquote>{turn.open_question}</blockquote>}{turn.next_agent && <small>Handoff → {turn.next_agent}</small>}</div>
                            </li>)}</ol>
                        </section>}
                    </div>
                </>}
            </section>
        </div>
    </main>;
}

export function openCalendar(): void {
    window.location.assign(meetingPath());
}
