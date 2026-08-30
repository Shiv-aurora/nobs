import React, {useMemo, useState} from 'react';

import {api, APIError} from '../api/client';
import type {Meeting, MeetingAgentMode, MeetingDelegation} from '../types/models';

const CAPABILITIES = [
    {id: 'answer_project_status', label: 'Answer project status'},
    {id: 'explain_confirmed_decisions', label: 'Explain confirmed decisions'},
    {id: 'share_customer_safe_status', label: 'Share customer-safe status'},
    {id: 'record_follow_up', label: 'Record follow-ups'},
];

const MODES: Array<{id: MeetingAgentMode; label: string; detail: string}> = [
    {id: 'listen', label: 'Listen for me', detail: 'Capture relevant outcomes and stay silent unless addressed.'},
    {id: 'represent', label: 'Represent me', detail: 'Answer routine questions inside your approved work context.'},
    {id: 'mission', label: 'Mission', detail: 'Represent you and make sure assigned questions get asked.'},
];

function lines(value: string): string[] {
    return value.split('\n').map((item) => item.trim()).filter(Boolean);
}

export function SendAgentModal({meeting, conflicts, onClose, onSaved}: {meeting: Meeting; conflicts: Meeting[]; onClose: () => void; onSaved: (delegation: MeetingDelegation) => void}): JSX.Element {
    const [mode, setMode] = useState<MeetingAgentMode>('mission');
    const [tell, setTell] = useState('API v2 is ready for QA.');
    const [ask, setAsk] = useState('Is mobile integration still on track for Thursday?');
    const [capabilities, setCapabilities] = useState<string[]>(['answer_project_status', 'explain_confirmed_decisions']);
    const [escalate, setEscalate] = useState('Someone wants to change the release date.\nA security decision is required.');
    const [working, setWorking] = useState(false);
    const [error, setError] = useState('');
    const selectedMode = useMemo(() => MODES.find((item) => item.id === mode) || MODES[1], [mode]);

    const submit = async () => {
        setWorking(true);
        setError('');
        try {
            const delegation = await api.createMeetingDelegation(meeting.id, {
                mode,
                tell: lines(tell),
                ask: lines(ask),
                capability_ids: capabilities,
                escalation_rules: lines(escalate),
            }, meeting.etag);
            onSaved(delegation);
        } catch (caught) {
            setError(caught instanceof APIError ? caught.message : 'Your agent could not be assigned to this meeting.');
        } finally {
            setWorking(false);
        }
    };

    return <div className='nobs-modal-backdrop' role='presentation' onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
        <section className='nobs-mission-modal' role='dialog' aria-modal='true' aria-labelledby='nobs-mission-title'>
            <header>
                <div>
                    <span className='nobs-eyebrow'>Send my Agent</span>
                    <h2 id='nobs-mission-title'>{meeting.title}</h2>
                    <p>{conflicts.length ? `You are double-booked with ${conflicts.map((item) => item.title).join(', ')}.` : 'Give your agent a clear, bounded mission.'}</p>
                </div>
                <button type='button' className='nobs-icon-button' aria-label='Close mission' onClick={onClose}><i className='icon-close'/></button>
            </header>

            <div className='nobs-mode-picker' role='radiogroup' aria-label='Agent mode'>
                {MODES.map((item) => <button key={item.id} type='button' role='radio' aria-checked={mode === item.id} className={mode === item.id ? 'is-active' : ''} onClick={() => setMode(item.id)}><strong>{item.label}</strong><span>{item.detail}</span></button>)}
            </div>
            <p className='nobs-mode-summary'><i className='icon-shield-outline'/> {selectedMode.detail}</p>

            <div className='nobs-mission-grid'>
                <label><strong>Tell them</strong><span>One update per line</span><textarea value={tell} onChange={(event) => setTell(event.target.value)} rows={3}/></label>
                <label><strong>Ask</strong><span>What your agent should bring back</span><textarea value={ask} onChange={(event) => setAsk(event.target.value)} rows={3}/></label>
                <fieldset><legend>You may</legend><span>These choices cannot override company permissions.</span><div className='nobs-capability-list'>{CAPABILITIES.map((capability) => <label key={capability.id}><input type='checkbox' checked={capabilities.includes(capability.id)} onChange={(event) => setCapabilities(event.target.checked ? [...capabilities, capability.id] : capabilities.filter((item) => item !== capability.id))}/><span>{capability.label}</span></label>)}</div></fieldset>
                <label><strong>Escalate if</strong><span>Company security and authority rules are always included.</span><textarea value={escalate} onChange={(event) => setEscalate(event.target.value)} rows={4}/></label>
            </div>

            {error && <div className='nobs-inline-error' role='alert'>{error}</div>}
            <footer><button type='button' className='nobs-secondary-button' onClick={onClose}>Cancel</button><button type='button' className='nobs-primary-button' disabled={working || capabilities.length === 0} onClick={() => void submit()}>{working ? 'Assigning agent…' : 'Send my Agent'}</button></footer>
        </section>
    </div>;
}
