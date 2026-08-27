import React from 'react';

import type {AuditEvent} from '../types/models';
import {AuditIcon, ShieldIcon} from './icons';
import {humanize, relativeTime} from '../utils/format';

interface Props {
    events: AuditEvent[];
}

export function AuditPage({events}: Props): JSX.Element {
    return <div className='np-page'><div className='np-page-intro'><span>Observability</span><h1>Audit trail</h1><p>See who asked, which delegates ran, what evidence was accessed, and where policy intervened.</p></div><div className='np-audit-list'>{events.length === 0 && <div className='np-empty-audit'><AuditIcon size={28}/><h3>No runs yet</h3><p>Ask the organization to generate a trace.</p></div>}{events.map((event) => <article className='np-audit-row' key={event.id}><span className={`np-audit-icon ${event.event_type.includes('security') ? 'is-security' : ''}`}>{event.event_type.includes('security') ? <ShieldIcon/> : <AuditIcon/>}</span><div><span>{humanize(event.event_type)}</span><h3>{event.summary}</h3><small>Actor: {event.actor_id} · Entities: {event.entity_ids.join(', ')}</small></div><time>{relativeTime(event.created_at)}</time></article>)}</div></div>;
}
