import React from 'react';

interface PostLike {
    props?: Record<string, unknown>;
}

export function PostIdentityBadge({post}: {post: PostLike}): JSX.Element | null {
    const props = post.props || {};
    if (props.noping_delivery_mode === 'human_only') {
        return <span className='np-post-badge is-human'>Human only</span>;
    }
    if (!props.noping_agent && !props.noping_agent_kind) {
        return null;
    }
    const representedName = typeof props.noping_represented_user_name === 'string' ? props.noping_represented_user_name : '';
    const firstName = representedName.trim().split(/\s+/)[0] || representedName;
    const label = representedName ? `${firstName}'s Agent` : props.noping_agent_kind === 'meeting' ? 'NoBS Meeting Agent' : 'NoBS Organization Agent';
    const consulted = typeof props.noping_agents_consulted === 'number' ? props.noping_agents_consulted : 0;
    const interrupted = typeof props.noping_people_interrupted === 'number' ? props.noping_people_interrupted : 0;
    const runID = typeof props.noping_run_id === 'string' ? props.noping_run_id : '';
    const modelName = typeof props.noping_model_name === 'string' ? props.noping_model_name : '';
    return <span className='np-post-agent-meta'><span className='np-post-badge is-agent' title={representedName ? `Representing ${representedName} through NoBS` : 'NoBS organizational delegate'}><span className='np-post-badge__mark'/> {label}</span>{modelName.startsWith('gemini') ? <span className='np-post-model' title={modelName}>Gemini</span> : null}{consulted > 0 && <button type='button' className='np-post-route-link' onClick={() => window.dispatchEvent(new CustomEvent('noping:open-panel', {detail: {runID}}))} title='Open NoBS route and evidence'>{consulted} delegates consulted · {interrupted} humans interrupted</button>}</span>;
}
