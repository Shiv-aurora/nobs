import React, {useEffect, useMemo, useRef, useState} from 'react';

import {api, APIError} from '../api/client';
import logo from '../assets/logo.png';
import pcmWorkletURL from '../worklets/pcm16.worklet.js';
import type {Meeting, MeetingDelegation, MeetingHandoff} from '../types/models';

interface LiveEvent {
    type: string;
    status?: string;
    text?: string;
    label?: string;
    message?: string;
    agent_label?: string;
    demo_mode?: boolean;
    handoff?: MeetingHandoff;
}

interface SpeechRecognitionEventLike {
    results: ArrayLike<{0: {transcript: string}}>;
}

type SpeechRecognitionLike = new () => {
    continuous: boolean;
    interimResults: boolean;
    lang: string;
    onresult: (event: SpeechRecognitionEventLike) => void;
    onerror: () => void;
    onend: () => void;
    start(): void;
    stop(): void;
};

function delegationIDFromPath(): string {
    const parts = window.location.pathname.split('/').filter(Boolean);
    return decodeURIComponent(parts[parts.length - 1] || '');
}

function calendarPath(): string {
    const team = window.location.pathname.split('/').filter(Boolean)[0] || 'acme';
    return `/${team}/nobs/calendar`;
}

function socketURL(delegationID: string, nonce: string): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/plugins/com.noping.enterprise/api/v1/live/meetings/${encodeURIComponent(delegationID)}?nonce=${encodeURIComponent(nonce)}`;
}

export function HuddlePage(): JSX.Element {
    const delegationID = useMemo(delegationIDFromPath, []);
    const [delegation, setDelegation] = useState<MeetingDelegation | null>(null);
    const [meeting, setMeeting] = useState<Meeting | null>(null);
    const [status, setStatus] = useState('Connecting');
    const [events, setEvents] = useState<LiveEvent[]>([]);
    const [handoff, setHandoff] = useState<MeetingHandoff | null>(null);
    const [question, setQuestion] = useState('What changed in AUTH-392, and is anything still blocking the merge?');
    const [error, setError] = useState('');
    const [micActive, setMicActive] = useState(false);
    const [demoMode, setDemoMode] = useState(false);
    const socketRef = useRef<WebSocket | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const inputContextRef = useRef<AudioContext | null>(null);
    const playbackContextRef = useRef<AudioContext | null>(null);
    const processorRef = useRef<AudioWorkletNode | null>(null);
    const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const reconnectAttemptsRef = useRef(0);
    const endingRef = useRef(false);
    const sourcesRef = useRef<AudioBufferSourceNode[]>([]);
    const nextPlaybackRef = useRef(0);

    const addEvent = (event: LiveEvent) => setEvents((current) => [...current.slice(-29), event]);

    const flushAudio = () => {
        sourcesRef.current.forEach((source) => {
            try {
                source.stop();
            } catch {
                // The source may already have completed.
            }
        });
        sourcesRef.current = [];
        nextPlaybackRef.current = 0;
    };

    const playPCM = async (data: ArrayBuffer) => {
        const context = playbackContextRef.current || new AudioContext({sampleRate: 24000});
        playbackContextRef.current = context;
        await context.resume();
        const samples = new Int16Array(data);
        const buffer = context.createBuffer(1, samples.length, 24000);
        const channel = buffer.getChannelData(0);
        for (let index = 0; index < samples.length; index += 1) {
            channel[index] = samples[index] / 32768;
        }
        const source = context.createBufferSource();
        source.buffer = buffer;
        source.connect(context.destination);
        const startAt = Math.max(context.currentTime, nextPlaybackRef.current || context.currentTime);
        nextPlaybackRef.current = startAt + buffer.duration;
        sourcesRef.current.push(source);
        source.onended = () => { sourcesRef.current = sourcesRef.current.filter((item) => item !== source); };
        source.start(startAt);
    };

    useEffect(() => {
        document.title = 'Agent huddle - NoBS';
        endingRef.current = false;
        const nonce = sessionStorage.getItem(`nobs-live-nonce:${delegationID}`) || '';
        api.meetingDelegation(delegationID).then((detail) => {
            setDelegation(detail.delegation);
            setMeeting(detail.meeting);
            setHandoff(detail.handoff || null);
            if (!nonce && !detail.handoff) {
                throw new APIError('This secure huddle link expired. Start it again from Calendar.', 401);
            }
            if (detail.handoff) {
                setStatus('Ended');
                return;
            }
            const connect = () => {
                const socket = new WebSocket(socketURL(delegationID, nonce));
                socket.binaryType = 'arraybuffer';
                socketRef.current = socket;
                socket.onopen = () => {
                    reconnectAttemptsRef.current = 0;
                    setError('');
                };
                socket.onmessage = (message) => {
                    if (message.data instanceof ArrayBuffer) {
                        void playPCM(message.data);
                        return;
                    }
                    const event = JSON.parse(String(message.data)) as LiveEvent;
                    if (event.type === 'session_state') {
                        setStatus(event.status || 'Live');
                        setDemoMode(Boolean(event.demo_mode));
                    } else if (event.type === 'interrupted') {
                        flushAudio();
                    } else if (event.type === 'handoff_ready' && event.handoff) {
                        endingRef.current = true;
                        setHandoff(event.handoff);
                        setStatus('Ended');
                        sessionStorage.removeItem(`nobs-live-nonce:${delegationID}`);
                    } else {
                        addEvent(event);
                        if ((event.type === 'agent_response' || event.type === 'escalation') && event.text && 'speechSynthesis' in window) {
                            window.speechSynthesis.cancel();
                            window.speechSynthesis.speak(new SpeechSynthesisUtterance(event.text));
                        }
                    }
                };
                socket.onclose = () => {
                    if (endingRef.current) {
                        return;
                    }
                    setStatus('Reconnecting');
                    reconnectAttemptsRef.current += 1;
                    if (reconnectAttemptsRef.current <= 5) {
                        reconnectTimerRef.current = setTimeout(connect, Math.min(5000, 750 * reconnectAttemptsRef.current));
                    } else {
                        setError('The live connection could not resume. Your mission and saved outcomes are safe.');
                    }
                };
                socket.onerror = () => setError('The live connection dropped. Reconnecting with your saved mission…');
            };
            connect();
        }).catch((caught) => setError(caught instanceof APIError ? caught.message : 'This agent huddle could not be opened.'));
        return () => {
            endingRef.current = true;
            if (reconnectTimerRef.current) {
                clearTimeout(reconnectTimerRef.current);
            }
            socketRef.current?.close();
            streamRef.current?.getTracks().forEach((track) => track.stop());
            processorRef.current?.disconnect();
            void inputContextRef.current?.close();
            void playbackContextRef.current?.close();
        };
    }, [delegationID]);

    const send = (event: Record<string, unknown>) => {
        if (socketRef.current?.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify(event));
        }
    };

    const startRawMicrophone = async () => {
        const stream = await navigator.mediaDevices.getUserMedia({audio: {channelCount: 1, echoCancellation: true, noiseSuppression: true}});
        streamRef.current = stream;
        const context = new AudioContext();
        inputContextRef.current = context;
        const source = context.createMediaStreamSource(stream);
        await context.audioWorklet.addModule(pcmWorkletURL);
        const processor = new AudioWorkletNode(context, 'nobs-pcm16');
        processorRef.current = processor;
        processor.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
            if (socketRef.current?.readyState === WebSocket.OPEN) {
                socketRef.current.send(event.data);
            }
        };
        source.connect(processor);
        const mutedOutput = context.createGain();
        mutedOutput.gain.value = 0;
        processor.connect(mutedOutput);
        mutedOutput.connect(context.destination);
        setMicActive(true);
    };

    const stopMicrophone = () => {
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        processorRef.current?.disconnect();
        processorRef.current = null;
        void inputContextRef.current?.close();
        inputContextRef.current = null;
        setMicActive(false);
    };

    const askWithVoice = async () => {
        if (micActive) {
            stopMicrophone();
            return;
        }
        flushAudio();
        window.speechSynthesis?.cancel();
        send({type: 'interrupt'});
        const speechWindow = window as typeof window & {SpeechRecognition?: SpeechRecognitionLike; webkitSpeechRecognition?: SpeechRecognitionLike};
        const Recognition = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
        if (!demoMode || !Recognition) {
            await startRawMicrophone();
            return;
        }
        const recognition = new Recognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        recognition.onresult = (event) => {
            const transcript = event.results[0]?.[0]?.transcript || '';
            setQuestion(transcript);
            send({type: 'utterance', text: transcript});
        };
        recognition.onerror = () => setError('Voice capture failed. You can type the same question below.');
        recognition.onend = () => setMicActive(false);
        setMicActive(true);
        recognition.start();
    };

    const pause = () => {
        const next = status.toLowerCase() === 'paused' ? 'resume' : 'pause';
        send({type: next});
        setStatus(next === 'pause' ? 'Paused' : 'Live');
    };

    const end = () => {
        stopMicrophone();
        send({type: 'end'});
    };
    const revoke = async () => {
        if (!delegation) {
            return;
        }
        endingRef.current = true;
        stopMicrophone();
        socketRef.current?.close();
        setHandoff(await api.revokeMeetingDelegation(delegation.id));
        setStatus('Ended');
    };

    if (handoff) {
        return <main className='nobs-huddle is-ended'><header className='nobs-huddle__topbar'><button type='button' onClick={() => window.location.assign(calendarPath())}><i className='icon-arrow-left'/> Calendar</button><strong>Meeting handoff</strong></header><section className='nobs-handoff'><img src={logo} alt=''/><span>YOUR AGENT ATTENDED</span><h1>{meeting?.title}</h1>{handoff.summary ? <p>{handoff.summary}</p> : null}<p>{handoff.meeting_minutes_avoided} meeting minutes avoided</p><div className='nobs-handoff__grid'><article><strong>Told</strong>{handoff.told.map((item) => <p key={item}>{item}</p>)}</article><article><strong>Asked</strong>{handoff.asked.map((item) => <p key={item}>{item}</p>)}</article><article><strong>Answers</strong>{handoff.answers.length ? handoff.answers.map((item) => <p key={item}>{item}</p>) : <p>No verified answer was recorded.</p>}</article><article className={handoff.escalations.length ? 'is-important' : ''}><strong>For you</strong>{handoff.for_you.length ? handoff.for_you.map((item) => <p key={item}>{item}</p>) : <p>Nothing requires your judgment.</p>}</article></div><button type='button' className='nobs-primary-button' onClick={() => window.location.assign(calendarPath())}>Back to Calendar</button></section></main>;
    }

    return <main className='nobs-huddle'>
        <header className='nobs-huddle__topbar'><button type='button' onClick={() => window.location.assign(calendarPath())}><i className='icon-arrow-left'/> Calendar</button><div><span className={`nobs-live-dot is-${status.toLowerCase()}`}/><strong>{meeting?.title || 'Agent huddle'}</strong><span>{status}</span></div><button type='button' className='is-danger' onClick={() => void revoke()}>Revoke agent</button></header>
        <div className='nobs-huddle__stage'>
            <section className='nobs-huddle__room'>
                <div className='nobs-agent-orb'><img src={logo} alt=''/><span className='nobs-agent-orb__pulse'/></div>
                <span className='nobs-eyebrow'>AI REPRESENTATIVE</span>
                <h1>{delegation ? `${delegation.represented_user_name}'s Agent` : 'Your Agent'}</h1>
                <p>{delegation ? `Representing ${delegation.represented_user_name} · ${delegation.mission.mode} mode` : 'Loading mission…'}</p>
                <div className='nobs-huddle__attendees'>{meeting?.attendees.map((attendee) => <span key={attendee.user_id}><i>{attendee.name.split(' ').map((part) => part[0]).join('').slice(0, 2)}</i>{attendee.name}</span>)}</div>
                <div className='nobs-huddle__controls'><button type='button' className={micActive ? 'is-active' : ''} onClick={() => void askWithVoice()}><i className='icon-microphone-outline'/><span>{micActive ? 'Listening' : 'Microphone'}</span></button><button type='button' onClick={pause}><i className={status.toLowerCase() === 'paused' ? 'icon-play-outline' : 'icon-pause'}/><span>{status.toLowerCase() === 'paused' ? 'Resume' : 'Pause agent'}</span></button><button type='button' className='is-end' onClick={end}><i className='icon-phone-hangup-outline'/><span>End</span></button></div>
            </section>
            <aside className='nobs-huddle__panel'>
                <header><strong>Mission</strong><span>Audio is never stored</span></header>
                <section><span className='nobs-eyebrow'>Tell them</span>{delegation?.mission.tell.map((item) => <p key={item}>{item}</p>)}</section>
                <section><span className='nobs-eyebrow'>Ask</span>{delegation?.mission.ask.map((item) => <p key={item}>{item}</p>)}</section>
                <section className='nobs-live-activity'><span className='nobs-eyebrow'>Live activity</span>{events.length ? events.map((event, index) => <article key={`${event.type}-${index}`} className={event.type === 'escalation' ? 'is-escalation' : ''}><i className={event.type === 'tool_state' ? 'icon-magnify' : event.type === 'escalation' ? 'icon-shield-alert-outline' : 'icon-robot-outline'}/><div><strong>{event.type === 'tool_state' ? event.label : event.type === 'escalation' ? 'Human judgment required' : 'Agent'}</strong><p>{event.text || event.message || (event.status === 'checking' ? 'Checking authorized context…' : 'Listening')}</p></div></article>) : <p className='nobs-muted'>The agent is listening for its scope and staying silent otherwise.</p>}</section>
                <form className='nobs-huddle__question' onSubmit={(event) => { event.preventDefault(); send({type: 'utterance', text: question}); }}><label htmlFor='nobs-live-question'>Demo a meeting question</label><div><input id='nobs-live-question' value={question} onChange={(event) => setQuestion(event.target.value)}/><button type='submit' aria-label='Ask agent'><i className='icon-send'/></button></div></form>
                {error && <div className='nobs-inline-error'>{error}</div>}
            </aside>
        </div>
    </main>;
}
