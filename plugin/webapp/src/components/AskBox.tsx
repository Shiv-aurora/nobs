import React, {useState, type ChangeEvent, type KeyboardEvent} from 'react';

import {ArrowIcon, SearchIcon, SparkIcon} from './icons';

interface Props {
    onSubmit: (text: string) => Promise<void>;
    loading: boolean;
    compact?: boolean;
}

const examples = [
    'Why has Atlas not shipped?',
    'Who is handling the Atlas blocker tonight?',
    'Can we bypass security review for the $200K customer?',
];

export function AskBox({onSubmit, loading, compact = false}: Props): JSX.Element {
    const [text, setText] = useState('');

    const submit = async (value = text) => {
        const trimmed = value.trim();
        if (trimmed.length < 3 || loading) {
            return;
        }
        setText(trimmed);
        await onSubmit(trimmed);
    };

    return (
        <section className={`np-ask-box ${compact ? 'is-compact' : ''}`}>
            {!compact && (
                <div className='np-ask-heading'>
                    <span className='np-ask-spark'><SparkIcon/></span>
                    <div><h1>Ask your company</h1><p>Get the answer without finding a channel or interrupting a coworker.</p></div>
                </div>
            )}
            <div className='np-query-input-wrap'>
                <SearchIcon/>
                <textarea
                    value={text}
                    onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setText(event.target.value)}
                    onKeyDown={(event: KeyboardEvent<HTMLTextAreaElement>) => {
                        if (event.key === 'Enter' && !event.shiftKey) {
                            event.preventDefault();
                            void submit();
                        }
                    }}
                    placeholder='What do you need to know or get done?'
                    rows={1}
                    aria-label='Ask your company'
                />
                <button type='button' onClick={() => void submit()} disabled={loading || text.trim().length < 3}>
                    {loading ? <span className='np-spinner'/> : <ArrowIcon/>}
                </button>
            </div>
            {!compact && (
                <div className='np-query-examples'>
                    <span>Try:</span>
                    {examples.map((example) => <button type='button' key={example} onClick={() => {setText(example); void submit(example);}}>{example}</button>)}
                </div>
            )}
        </section>
    );
}
