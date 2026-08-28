import React, {useState} from 'react';

import type {BootstrapResponse} from '../types/models';
import {ProjectCard} from './ProjectCard';

interface Props {
    bootstrap: BootstrapResponse;
    mode: 'projects' | 'people';
}

const people = [
    {id: 'sarah', initials: 'SC', name: 'Sarah Chen', title: 'Security Lead', state: 'Out today', detail: 'Alex holds Atlas approval authority', focus: 'Closing Atlas launch risk without weakening SEC-POL-12', project: 'Project Atlas · Security readiness', blocker: 'Penetration-test report SEC-184 is still pending', availability: 'OOO until Aug 28, 9:00 AM ET', expertise: ['Security architecture', 'Risk exceptions', 'Data controls'], answerable: ['Current Atlas security status', 'Who has delegated approval authority', 'Relevant launch controls'], evidence: ['Google Calendar · OOO block', 'Security Review · SEC-184 update', 'Authority map · Alex delegated']},
    {id: 'alex', initials: 'AM', name: 'Alex Morgan', title: 'Staff Security Engineer', state: 'Available', detail: 'Acting security approver until tomorrow', focus: 'Reviewing the final Atlas security exception path', project: 'Project Atlas · Security review', blocker: 'Awaiting penetration-test report', availability: 'Available · acting approver through 6:00 PM ET', expertise: ['Application security', 'Threat modeling', 'Security review'], answerable: ['Security gate status', 'Exception requirements', 'Approval ownership'], evidence: ['Authority map · temporary delegation', 'SEC-184 · latest review note']},
    {id: 'daniel', initials: 'DK', name: 'Daniel Kim', title: 'Mobile Engineer', state: 'Fix in review', detail: 'AUTH-392 · PR #892', focus: 'Shipping the mobile authentication fix', project: 'Project Atlas · Mobile launch', blocker: 'PR #892 requires final review', availability: 'Available · heads-down until 3:00 PM', expertise: ['iOS', 'Authentication', 'Mobile release'], answerable: ['AUTH-392 status', 'PR #892 evidence', 'Expected merge window'], evidence: ['GitHub · PR #892', 'Jira · AUTH-392']},
    {id: 'priya', initials: 'PS', name: 'Priya Shah', title: 'Senior Product Manager', state: 'Available', detail: 'Owns Project Atlas', focus: 'Balancing the Northstar launch request with remaining risk', project: 'Project Atlas · Launch coordination', blocker: 'Security approval is the only open gate', availability: 'Available · next meeting at 4:30 PM', expertise: ['Product strategy', 'Enterprise launches', 'Atlas roadmap'], answerable: ['Launch scope', 'Customer impact', 'Target date and ownership'], evidence: ['Atlas plan · target date', 'Northstar account note · $200K expansion']},
];

export function OrganizationPage({bootstrap, mode}: Props): JSX.Element {
    const [selectedID, setSelectedID] = useState('sarah');
    const atlasState = bootstrap.work_states.find((item) => item.entity_id === 'atlas');
    const selected = people.find((person) => person.id === selectedID) || people[0];
    const selectedState = bootstrap.work_states.find((item) => item.entity_id === selected.id);
    if (mode === 'projects') {
        return <div className='np-page'><div className='np-page-intro'><span>Organization</span><h1>Projects and teams</h1><p>Each entity maintains a permission-aware delegate and semantic work state.</p></div><div className='np-card-stack'>{bootstrap.projects.map((project) => <ProjectCard project={project} state={atlasState} key={project.id}/>)}</div><div className='np-team-grid'>{['Engineering', 'Security', 'Product', 'Customer Support'].map((team) => <article className='np-team-card' key={team}><span>{team.slice(0, 2).toUpperCase()}</span><div><h3>{team}</h3><p>Delegate ready · cross-team routing enabled</p></div></article>)}</div></div>;
    }
    return <div className='np-page'><div className='np-page-intro'><span>Live employee context</span><h1>People and delegates</h1><p>Ask what a person’s delegate already knows before taking their attention.</p></div><div className='np-people-layout'><div className='np-people-list'>{people.map((person) => <button type='button' className={`np-person-card ${selected.id === person.id ? 'is-selected' : ''}`} key={person.id} onClick={() => setSelectedID(person.id)}><span className={`np-person-avatar is-${person.id}`}>{person.initials}</span><span className='np-person-summary'><strong>{person.name}</strong><small>{person.title}</small><em>{person.state}</em></span><span className='np-person-open'>View →</span></button>)}</div><article className='np-delegate-profile'>
        <div className='np-delegate-hero'><span className={`np-person-avatar is-${selected.id}`}>{selected.initials}</span><div><span>Personal delegate · live</span><h2>{selected.name}</h2><p>{selected.title}</p></div><span className='np-live-badge'><i/>Updated now</span></div>
        <div className='np-delegate-focus'><span>Current focus</span><h3>{selectedState?.headline || selected.focus}</h3><p>{selectedState?.detail || selected.project}</p></div>
        <div className='np-delegate-grid'><div><span>Project</span><strong>{selected.project}</strong></div><div><span>Active blocker</span><strong className='is-blocked'>{selected.blocker}</strong></div><div><span>Availability / OOO</span><strong>{selected.availability}</strong></div><div><span>Confidence</span><strong>{Math.round((selectedState?.confidence || .94) * 100)}% · evidence-backed</strong></div></div>
        <div className='np-delegate-columns'><section><span>Expertise</span><div className='np-tag-list'>{selected.expertise.map((item) => <span key={item}>{item}</span>)}</div></section><section><span>Delegate can answer without interrupting</span><ul>{selected.answerable.map((item) => <li key={item}>{item}</li>)}</ul></section></div>
        <section className='np-recent-evidence'><div><span>Recent evidence</span><small>Permission-filtered · newest first</small></div>{selected.evidence.map((item, index) => <div className='np-evidence-signal' key={item}><i className={index === 0 ? 'is-new' : ''}/><span><strong>{item}</strong><small>{index === 0 ? '12 minutes ago' : index === 1 ? '2 hours ago' : 'Yesterday'}</small></span></div>)}</section>
    </article></div></div>;
}
