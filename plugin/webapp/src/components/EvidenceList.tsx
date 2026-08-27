import React from 'react';

import type {Evidence} from '../types/models';
import {ExternalIcon, ShieldIcon} from './icons';
import {percent, relativeTime} from '../utils/format';

interface Props {
    evidence: Evidence[];
}

export function EvidenceList({evidence}: Props): JSX.Element {
    return (
        <div className='np-evidence'>
            <div className='np-section-label'><span>Evidence</span><small>{evidence.length} authorized sources</small></div>
            <div className='np-evidence-list'>
                {evidence.map((item) => (
                    <a className='np-evidence-row' href={item.source_url} key={item.id}>
                        <span className='np-evidence-type'><ShieldIcon size={16}/></span>
                        <span className='np-evidence-copy'><strong>{item.title}</strong><small>{item.source_type.replaceAll('_', ' ')} · {relativeTime(item.observed_at)}</small></span>
                        <span className='np-confidence'>{percent(item.confidence)}</span>
                        <ExternalIcon/>
                    </a>
                ))}
            </div>
        </div>
    );
}
