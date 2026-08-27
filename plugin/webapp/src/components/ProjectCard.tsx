import React from 'react';

import type {Project, SemanticWorkState} from '../types/models';
import {ClockIcon, ProjectIcon} from './icons';

interface Props {
    project: Project;
    state?: SemanticWorkState;
}

export function ProjectCard({project, state}: Props): JSX.Element {
    return (
        <article className='np-project-card'>
            <div className='np-project-icon'><ProjectIcon size={22}/></div>
            <div className='np-project-copy'>
                <div className='np-project-title'><h3>{project.name}</h3><span className={`np-health is-${project.health}`}>{project.health.replace('_', ' ')}</span></div>
                <p>{project.summary}</p>
                <div className='np-project-state'>
                    <span className='np-blocker-dot'/>
                    <span><strong>{state?.headline || 'Project status available'}</strong><small>{state?.detail || project.status}</small></span>
                </div>
            </div>
            <div className='np-project-date'><ClockIcon size={15}/><span>Target {project.target_date}</span></div>
        </article>
    );
}
