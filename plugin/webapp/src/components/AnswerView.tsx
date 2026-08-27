import React from 'react';

import type {QueryResult} from '../types/models';
import {CheckIcon, ClockIcon, ShieldIcon, SparkIcon} from './icons';
import {EvidenceList} from './EvidenceList';
import {RouteTrace} from './RouteTrace';

interface Props {
    result: QueryResult;
    onOpenNeeds: () => void;
}

export function AnswerView({result, onOpenNeeds}: Props): JSX.Element {
    const statusClass = `is-${result.status}`;
    return (
        <section className={`np-answer ${statusClass}`}>
            <div className='np-answer-query'>
                <span>You asked</span>
                <p>{result.query}</p>
            </div>
            <div className='np-answer-card'>
                <div className='np-answer-head'>
                    <span className='np-answer-icon'>{result.status === 'refused' ? <ShieldIcon/> : <SparkIcon/>}</span>
                    <div><span>{result.headline}</span><h2>{result.answer}</h2></div>
                </div>
                <div className='np-answer-facts'>
                    <span><CheckIcon size={15}/>{Math.round(result.confidence * 100)}% confidence</span>
                    <span><ClockIcon size={15}/>{result.freshness_label}</span>
                    <span className={result.people_interrupted === 0 ? 'is-saved' : 'is-human'}>{result.people_interrupted} {result.people_interrupted === 1 ? 'person' : 'people'} interrupted</span>
                    {result.cached && <span className='is-cached'>Decision memory</span>}
                </div>
                {result.security_findings.length > 0 && (
                    <div className='np-security-banner'><ShieldIcon/><span><strong>Untrusted content blocked</strong><small>{result.security_findings[0].reason}</small></span></div>
                )}
                {result.policy_result && <div className='np-policy-result'><strong>Policy outcome</strong><span>{result.policy_result}</span></div>}
                {result.route.length > 0 && <RouteTrace route={result.route}/>} 
                {result.evidence.length > 0 && <EvidenceList evidence={result.evidence}/>} 
                {result.status === 'escalated' && (
                    <button className='np-primary-button np-decision-cta' type='button' onClick={onOpenNeeds}>
                        Open decision workflow
                    </button>
                )}
            </div>
        </section>
    );
}
