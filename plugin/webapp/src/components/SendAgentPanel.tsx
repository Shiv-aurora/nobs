import React, {useEffect, useMemo, useState} from 'react';

import {api, APIError} from '../api/client';
import logo from '../assets/logo.png';
import type {LiveMeetingSession, Meeting, MeetingDelegation} from '../types/models';

function lines(value: string): string[] {
    return value.split('\n').map((item) => item.trim()).filter(Boolean);
}

function meetingTime(meeting: Meeting): string {
    return new Intl.DateTimeFormat(undefined, {weekday: 'short', hour: 'numeric', minute: '2-digit'}).format(new Date(meeting.start_at));
}

function calendarPath(): string {
    const team = window.location.pathname.split('/').filter(Boolean)[0] || 'acme';
    return `/${team}/nobs/calendar`;
}

export function SendAgentPanel(): JSX.Element {
    const [meetings, setMeetings] = useState<Meeting[]>([]);
    const [selectedID, setSelectedID] = useState('');
    const [tell, setTell] = useState('Share my latest project update and current ownership.');
    const [ask, setAsk] = useState('What decisions or follow-ups should I know about?');
    const [delegation, setDelegation] = useState<MeetingDelegation | null>(null);
    const [session, setSession] = useState<LiveMeetingSession | null>(null);
    const [working, setWorking] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        void api.meetings().then((items) => {
            const eligible = items.filter((item) => item.preparation_eligibility !== 'skipped');
            setMeetings(eligible);
            setSelectedID(eligible[0]?.id || '');
        }).catch((caught) => setError(caught instanceof APIError ? caught.message : 'Meetings are temporarily unavailable.'));
    }, []);

    useEffect(() => {
        if (!delegation || session?.provider !== 'google_meet' || !['queued', 'joining', 'awaiting_admission', 'live'].includes(session.join_status)) {
            return undefined;
        }
        const timer = window.setInterval(() => {
            void api.meetingDelegation(delegation.id).then((detail) => {
                setDelegation(detail.delegation);
                setSession(detail.session || null);
            }).catch(() => undefined);
        }, 1500);
        return () => window.clearInterval(timer);
    }, [delegation?.id, session?.join_status, session?.provider]);

    const selected = useMemo(() => meetings.find((meeting) => meeting.id === selectedID), [meetings, selectedID]);

    const submit = async () => {
        if (!selected) {
            return;
        }
        setWorking(true);
        setError('');
        try {
            const created = await api.createMeetingDelegation(selected.id, {
                mode: 'mission',
                tell: lines(tell),
                ask: lines(ask),
                capability_ids: ['answer_project_status', 'explain_confirmed_decisions', 'record_follow_up'],
                escalation_rules: ['A security or release-date decision is required.', 'The agent cannot verify an answer from approved evidence.'],
            }, selected.etag);
            setDelegation(created);
            const started = await api.startMeetingDelegation(created.id);
            setDelegation(started.delegation);
            setSession(started.session);
            if (started.session.provider === 'in_app') {
                sessionStorage.setItem(`nobs-live-nonce:${started.delegation.id}`, started.session_nonce);
                const team = window.location.pathname.split('/').filter(Boolean)[0] || 'acme';
                window.location.assign(`/${team}/nobs/huddle/${encodeURIComponent(started.delegation.id)}`);
            }
        } catch (caught) {
            setError(caught instanceof APIError ? caught.message : 'Your agent could not be assigned.');
        } finally {
            setWorking(false);
        }
    };

    if (delegation && selected) {
        const googleMeet = session?.provider === 'google_meet';
        const meetStatus = session?.join_status === 'live' ? 'Live in Google Meet' : session?.join_status === 'awaiting_admission' ? 'Waiting for host admission' : session?.join_status === 'failed' ? (session.join_error || 'Google Meet join failed') : 'Google Meet join requested';
        return <div className='np-native-panel__body np-send-agent-body'>
            <section className='np-send-agent-success'>
                <img src={logo} alt=''/>
                <span>{googleMeet ? meetStatus : 'Agent started'}</span>
                <strong>{selected.title}</strong>
                <p>{googleMeet ? 'NoBS reports live only after the Meet participant is admitted. Calendar RSVP remains unchanged.' : 'Your permission-bound agent is active in the secure NoBS huddle. Calendar RSVP remains unchanged.'}</p>
                <button type='button' className='np-panel-primary' onClick={() => window.location.assign(calendarPath())}>Open meeting mission</button>
                <button type='button' className='np-panel-link' onClick={() => { setDelegation(null); setSession(null); }}>Send to another meeting</button>
            </section>
        </div>;
    }

    return <div className='np-native-panel__body np-send-agent-body'>
        <section className='np-send-agent-intro'>
            <span>Upcoming meetings</span>
            <strong>Be in two places at once</strong>
            <p>Your agent can listen, answer within your permissions, and bring back the questions that need you.</p>
        </section>

        <div className='np-send-agent-meetings' role='radiogroup' aria-label='Choose a meeting'>
            {meetings.map((meeting) => <button key={meeting.id} type='button' role='radio' aria-checked={meeting.id === selectedID} className={meeting.id === selectedID ? 'is-active' : ''} onClick={() => setSelectedID(meeting.id)}>
                <i className='icon-calendar-outline' aria-hidden='true'/>
                <span><strong>{meeting.title}</strong><small>{meetingTime(meeting)} · {meeting.attendees.length} people</small></span>
                {Object.values(meeting.attendance_plans || {}).includes('agent') ? <em>Assigned</em> : null}
            </button>)}
            {!meetings.length && !error ? <div className='np-send-agent-empty'>No eligible meetings are coming up.</div> : null}
        </div>

        {selected ? <section className='np-panel-section np-send-agent-mission'>
            <label><strong>What should your agent share?</strong><textarea value={tell} rows={3} onChange={(event) => setTell(event.target.value)} placeholder='One update per line'/></label>
            <label><strong>What should it ask?</strong><textarea value={ask} rows={3} onChange={(event) => setAsk(event.target.value)} placeholder='Specific questions to bring back'/></label>
            <div className='np-send-agent-boundary'><i className='icon-shield-outline'/>Company permissions and mandatory escalation rules always apply.</div>
            <button type='button' className='np-panel-primary' disabled={working || (!lines(tell).length && !lines(ask).length)} onClick={() => void submit()}>{working ? (selected.conference_uri ? 'Joining Google Meet…' : 'Starting agent…') : 'Send my Agent'}</button>
        </section> : null}
        {error ? <div className='np-panel-error' role='alert'>{error}</div> : null}
    </div>;
}
