import React from 'react';

import type {BootstrapResponse} from '../types/models';
import {ProjectCard} from './ProjectCard';

interface Props {
    bootstrap: BootstrapResponse;
    mode: 'projects' | 'people';
}

const people = [
    {id: 'sarah', initials: 'SC', name: 'Sarah Chen', title: 'Security Lead', state: 'Out today', detail: 'Alex holds Atlas approval authority'},
    {id: 'alex', initials: 'AM', name: 'Alex Morgan', title: 'Staff Security Engineer', state: 'Available', detail: 'Acting security approver until tomorrow'},
    {id: 'daniel', initials: 'DK', name: 'Daniel Kim', title: 'Mobile Engineer', state: 'Fix in review', detail: 'AUTH-392 · PR #892'},
    {id: 'priya', initials: 'PS', name: 'Priya Shah', title: 'Senior Product Manager', state: 'Available', detail: 'Owns Project Atlas'},
];

export function OrganizationPage({bootstrap, mode}: Props): JSX.Element {
    const atlasState = bootstrap.work_states.find((item) => item.entity_id === 'atlas');
    if (mode === 'projects') {
        return <div className='np-page'><div className='np-page-intro'><span>Organization</span><h1>Projects and teams</h1><p>Each entity maintains a permission-aware delegate and semantic work state.</p></div><div className='np-card-stack'>{bootstrap.projects.map((project) => <ProjectCard project={project} state={atlasState} key={project.id}/>)}</div><div className='np-team-grid'>{['Engineering', 'Security', 'Product', 'Customer Support'].map((team) => <article className='np-team-card' key={team}><span>{team.slice(0, 2).toUpperCase()}</span><div><h3>{team}</h3><p>Delegate ready · cross-team routing enabled</p></div></article>)}</div></div>;
    }
    return <div className='np-page'><div className='np-page-intro'><span>Directory</span><h1>People and delegates</h1><p>Know what someone owns and when their attention is actually required.</p></div><div className='np-people-grid'>{people.map((person) => <article className='np-person-card' key={person.id}><span className={`np-person-avatar is-${person.id}`}>{person.initials}</span><div><h3>{person.name}</h3><p>{person.title}</p><strong>{person.state}</strong><small>{person.detail}</small></div><button type='button'>View delegate</button></article>)}</div></div>;
}
