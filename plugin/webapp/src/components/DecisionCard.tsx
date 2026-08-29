import React, {useState, type ChangeEvent} from 'react';

import type {Decision} from '../types/models';
import {ClockIcon, ShieldIcon} from './icons';

interface Props {
    decision: Decision;
    onResolve: (decisionID: string, status: string, rationale: string) => Promise<void>;
}

export function DecisionCard({decision, onResolve}: Props): JSX.Element {
    const [rationale, setRationale] = useState('SEC-184 must complete; revenue urgency does not justify bypassing the control.');
    const [resolving, setResolving] = useState(false);

    const resolve = async (status: string) => {
        setResolving(true);
        try {
            await onResolve(decision.id, status, rationale);
        } finally {
            setResolving(false);
        }
    };

    return (
        <article className='np-decision-card'>
            <div className='np-decision-ribbon'>Decision required</div>
            <div className='np-decision-header'>
                <span className='np-decision-icon'><ShieldIcon/></span>
                <div><span>Project Atlas · Security</span><h2>{decision.title}</h2><p>{decision.summary}</p></div>
                <span className='np-due'><ClockIcon size={14}/> Due in 2h</span>
            </div>
            <div className='np-decision-context'>
                <div><span>Customer value</span><strong>$200K</strong></div>
                <div><span>Engineering</span><strong className='is-good'>Ready</strong></div>
                <div><span>Security</span><strong className='is-warn'>Pending</strong></div>
                <div><span>Control</span><strong>SEC-POL-12</strong></div>
            </div>
            {decision.handoff_packet_id && <div className='np-handoff-summary'><span>Agent-to-agent handoff packet</span><strong>Context assembled before interrupting you</strong><small>Evidence checked · attempted routes · policy boundary · requested judgment</small></div>}
            <div className='np-memory-contract'><span>What NoBS will learn from this decision</span><div><strong>Scope</strong><small>Atlas · security exceptions</small></div><div><strong>Evidence</strong><small>SEC-184 + SEC-POL-12</small></div><div><strong>Decision maker</strong><small>You · acting authority</small></div><div><strong>Review</strong><small>30 days · expires automatically</small></div></div>
            <label className='np-rationale'>
                <span>Decision rationale</span>
                <textarea value={rationale} onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setRationale(event.target.value)} rows={2}/>
            </label>
            <div className='np-decision-actions'>
                <button type='button' className='np-ghost-button' onClick={() => void resolve('discuss')} disabled={resolving}>Discuss</button>
                <button type='button' className='np-negative-button' onClick={() => void resolve('rejected')} disabled={resolving}>Reject exception</button>
                <button type='button' className='np-primary-button' onClick={() => void resolve('approved')} disabled={resolving}>Approve exception</button>
            </div>
        </article>
    );
}
