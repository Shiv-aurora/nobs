import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';

import {api, APIError} from '../api/client';
import {mattermost, MattermostAPIError} from '../api/mattermost';
import logo from '../assets/logo.png';
import type {MattermostChannel, MattermostPost, MattermostUser, MessagingBootstrap} from '../types/messaging';
import {SearchIcon} from './icons';

interface Props {
    onNeedsYou: () => void;
    needsCount: number;
}

function displayName(user?: MattermostUser): string {
    if (!user) {
        return 'Unknown teammate';
    }
    return [user.first_name, user.last_name].filter(Boolean).join(' ') || user.nickname || user.username;
}

function initials(user?: MattermostUser): string {
    return displayName(user).split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase();
}

function timeLabel(timestamp: number): string {
    return new Intl.DateTimeFormat(undefined, {hour: 'numeric', minute: '2-digit'}).format(new Date(timestamp));
}

function isAgentPost(post: MattermostPost): boolean {
    return post.props?.noping_agent === true || post.props?.noping_agent === 'true';
}

function cleanMessage(message: string): string {
    return message.replace(/\n*`noping-seed-[^`]+`\s*$/i, '').trim();
}

export function MessagesPage({onNeedsYou, needsCount}: Props): JSX.Element {
    const [workspace, setWorkspace] = useState<MessagingBootstrap | null>(null);
    const [selectedID, setSelectedID] = useState('');
    const [posts, setPosts] = useState<MattermostPost[]>([]);
    const [users, setUsers] = useState<Record<string, MattermostUser>>({});
    const [search, setSearch] = useState('');
    const [message, setMessage] = useState('');
    const [replyingTo, setReplyingTo] = useState<MattermostPost | null>(null);
    const [loading, setLoading] = useState(true);
    const [sending, setSending] = useState(false);
    const [agentThinking, setAgentThinking] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const bottomRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        let cancelled = false;
        void mattermost.bootstrap().then((next) => {
            if (cancelled) {
                return;
            }
            setWorkspace(next);
            const preferred = next.channels.find((channel) => channel.name === 'project-atlas') || next.channels.find((channel) => channel.name === 'town-square') || next.channels[0];
            setSelectedID(preferred?.id || '');
            setUsers({[next.currentUser.id]: next.currentUser});
            setError(null);
        }).catch((caught) => {
            if (!cancelled) {
                setError(caught instanceof MattermostAPIError ? caught.message : 'NoPing could not load your channels.');
            }
        }).finally(() => !cancelled && setLoading(false));
        return () => { cancelled = true; };
    }, []);

    const loadPosts = useCallback(async (channelID: string, quiet = false) => {
        if (!channelID) {
            return;
        }
        if (!quiet) {
            setLoading(true);
        }
        try {
            const response = await mattermost.posts(channelID);
            const ordered = response.order.map((id) => response.posts[id]).filter((post) => Boolean(post) && post.type === '').reverse();
            setPosts(ordered);
            const missingIDs = Array.from(new Set(ordered.map((post) => post.user_id).filter((id) => id && !users[id])));
            if (missingIDs.length) {
                const loadedUsers = await mattermost.users(missingIDs);
                setUsers((current) => ({...current, ...Object.fromEntries(loadedUsers.map((user) => [user.id, user]))}));
            }
            setError(null);
        } catch (caught) {
            if (!quiet) {
                setError(caught instanceof MattermostAPIError ? caught.message : 'Messages could not be loaded.');
            }
        } finally {
            if (!quiet) {
                setLoading(false);
            }
        }
    }, [users]);

    useEffect(() => {
        setReplyingTo(null);
        void loadPosts(selectedID);
        if (!selectedID) {
            return;
        }
        const interval = window.setInterval(() => void loadPosts(selectedID, true), 5000);
        return () => window.clearInterval(interval);
    }, [selectedID]);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({block: 'nearest'});
    }, [posts.length, agentThinking]);

    const selectedChannel = workspace?.channels.find((channel) => channel.id === selectedID) || null;
    const publicChannels = useMemo(() => (workspace?.channels || []).filter((channel) => channel.type === 'O' || channel.type === 'P').sort((a, b) => a.display_name.localeCompare(b.display_name)), [workspace]);
    const directChannels = useMemo(() => (workspace?.channels || []).filter((channel) => channel.type === 'D' || channel.type === 'G'), [workspace]);
    const filteredChannels = publicChannels.filter((channel) => channel.display_name.toLowerCase().includes(search.toLowerCase()));
    const postByID = useMemo(() => Object.fromEntries(posts.map((post) => [post.id, post])), [posts]);

    const send = async () => {
        const text = message.trim();
        if (!text || !selectedChannel || sending) {
            return;
        }
        const rootID = replyingTo ? (replyingTo.root_id || replyingTo.id) : '';
        setMessage('');
        setReplyingTo(null);
        setSending(true);
        try {
            const created = await mattermost.createPost(selectedChannel.id, text, rootID);
            setPosts((current) => [...current, created]);
            if (/^@noping\b/i.test(text)) {
                setAgentThinking(true);
                await api.agentReply(text, selectedChannel.id, created.id, rootID || created.id);
            }
            await loadPosts(selectedChannel.id, true);
            setError(null);
        } catch (caught) {
            setMessage(text);
            setError(caught instanceof APIError || caught instanceof MattermostAPIError ? caught.message : 'Your message could not be sent.');
        } finally {
            setSending(false);
            setAgentThinking(false);
        }
    };

    if (loading && !workspace) {
        return <div className='np-messages-loading'><img src={logo} alt=''/><strong>Opening your conversations</strong></div>;
    }

    return (
        <section className='np-messaging-shell'>
            <aside className='np-channel-sidebar'>
                <div className='np-channel-workspace'>
                    <div><strong>{workspace?.team.display_name || 'NoPing'}</strong><span>Company workspace</span></div>
                    <button type='button' aria-label='Workspace menu'>⌄</button>
                </div>
                <label className='np-channel-search'><SearchIcon size={16}/><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder='Find a channel'/></label>
                <button type='button' className='np-channel-needs' onClick={onNeedsYou}>
                    <span className='np-channel-needs-icon'>✓</span><span><strong>Needs you</strong><small>Decisions, not unread noise</small></span>{needsCount > 0 && <b>{needsCount}</b>}
                </button>
                <div className='np-channel-section'>
                    <div className='np-channel-section-label'><span>Channels</span><button type='button' aria-label='Add channel'>+</button></div>
                    {filteredChannels.map((channel) => <ChannelButton key={channel.id} channel={channel} active={channel.id === selectedID} onClick={() => setSelectedID(channel.id)}/>) }
                </div>
                {directChannels.length > 0 && <div className='np-channel-section'><div className='np-channel-section-label'><span>Direct messages</span><button type='button' aria-label='New direct message'>+</button></div>{directChannels.map((channel) => <ChannelButton key={channel.id} channel={channel} active={channel.id === selectedID} onClick={() => setSelectedID(channel.id)}/>)}</div>}
                <div className='np-channel-profile'><span className='np-presence-dot'/><div><strong>{displayName(workspace?.currentUser)}</strong><small>Available · delegate active</small></div></div>
            </aside>
            <div className='np-conversation'>
                <header className='np-conversation-header'>
                    <div><h1>{selectedChannel?.type === 'O' || selectedChannel?.type === 'P' ? '#' : ''} {selectedChannel?.display_name || 'Messages'}</h1><p>{selectedChannel?.purpose || 'A shared conversation with teammates and delegates.'}</p></div>
                    <div className='np-conversation-actions'><button type='button' className='np-agent-button' onClick={() => setMessage('@noping ')}><img src={logo} alt=''/><span>Ask NoPing</span></button><button type='button' aria-label='Search channel'><SearchIcon size={18}/></button></div>
                </header>
                <div className='np-message-list' aria-live='polite'>
                    {error && <div className='np-message-error'>{error}<button type='button' onClick={() => void loadPosts(selectedID)}>Retry</button></div>}
                    {selectedChannel && <div className='np-channel-opening'><div className='np-channel-opening-icon'>#</div><h2>{selectedChannel.display_name}</h2><p>{selectedChannel.purpose || `This is the beginning of the ${selectedChannel.display_name} channel.`}</p><span>NoPing delegates can answer routine questions here without interrupting a teammate.</span></div>}
                    {posts.map((post) => <MessageRow key={post.id} post={post} user={users[post.user_id]} parent={post.root_id ? postByID[post.root_id] : undefined} onReply={() => setReplyingTo(post)} onAsk={() => { setReplyingTo(post); setMessage('@noping '); }}/>) }
                    {agentThinking && <div className='np-message-row is-agent is-thinking'><img className='np-message-avatar' src={logo} alt=''/><div className='np-message-body'><div className='np-message-meta'><strong>NoPing Agent</strong><span className='np-agent-label'>AI delegate</span></div><div className='np-agent-thinking'><i/><i/><i/><span>Consulting the right delegates…</span></div></div></div>}
                    <div ref={bottomRef}/>
                </div>
                <footer className='np-composer-wrap'>
                    {replyingTo && <div className='np-reply-context'><span>Replying to <strong>{displayName(users[replyingTo.user_id])}</strong></span><button type='button' onClick={() => setReplyingTo(null)}>×</button></div>}
                    <div className={`np-message-composer ${/^@noping\b/i.test(message) ? 'is-agent-query' : ''}`}>
                        <textarea value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void send(); } }} placeholder={`Message ${selectedChannel?.display_name ? `#${selectedChannel.display_name}` : 'channel'}`} rows={1}/>
                        <div className='np-composer-tools'><div><button type='button' aria-label='Add attachment'>＋</button><button type='button' onClick={() => setMessage((current) => current.startsWith('@noping') ? current : `@noping ${current}`)}><img src={logo} alt=''/>Ask agent</button></div><button type='button' className='np-send-message' disabled={!message.trim() || sending} onClick={() => void send()}>{sending ? 'Sending…' : 'Send'}</button></div>
                    </div>
                    <small className='np-composer-hint'><strong>@noping</strong> asks the organization first. Humans are interrupted only when their judgment is required.</small>
                </footer>
            </div>
        </section>
    );
}

function ChannelButton({channel, active, onClick}: {channel: MattermostChannel; active: boolean; onClick: () => void}): JSX.Element {
    return <button type='button' className={`np-channel-item ${active ? 'is-active' : ''}`} onClick={onClick}><span>{channel.type === 'O' || channel.type === 'P' ? '#' : '○'}</span><strong>{channel.display_name}</strong>{channel.name === 'project-atlas' && <i>3</i>}</button>;
}

function MessageRow({post, user, parent, onReply, onAsk}: {post: MattermostPost; user?: MattermostUser; parent?: MattermostPost; onReply: () => void; onAsk: () => void}): JSX.Element {
    const agent = isAgentPost(post);
    const route = typeof post.props?.noping_route === 'string' ? post.props.noping_route : '';
    const agentsConsulted = Number(post.props?.noping_agents_consulted || 0);
    const peopleInterrupted = Number(post.props?.noping_people_interrupted || 0);
    return (
        <article className={`np-message-row ${post.root_id ? 'is-reply' : ''} ${agent ? 'is-agent' : ''}`}>
            {agent ? <img className='np-message-avatar' src={logo} alt='NoPing'/> : <span className='np-message-avatar is-initials'>{initials(user)}</span>}
            <div className='np-message-body'>
                {parent && <div className='np-reply-line'>↳ replying to {cleanMessage(parent.message).slice(0, 70)}{cleanMessage(parent.message).length > 70 ? '…' : ''}</div>}
                <div className='np-message-meta'><strong>{agent ? 'NoPing Agent' : displayName(user)}</strong>{agent && <span className='np-agent-label'>AI delegate</span>}<time>{timeLabel(post.create_at)}</time></div>
                <div className='np-message-text'>{cleanMessage(post.message)}</div>
                {agent && <div className='np-agent-proof'>{route && <span className='np-agent-route'>You → {route}</span>}<span><strong>{agentsConsulted || 'Multiple'} agents consulted</strong> · {peopleInterrupted} humans interrupted</span></div>}
                <div className='np-message-actions'><button type='button' onClick={onReply}>Reply</button>{!agent && <button type='button' onClick={onAsk}>Ask NoPing about this</button>}</div>
            </div>
        </article>
    );
}
