import React from 'react';

interface Props {
    label: string;
    value: string;
    detail: string;
    emphasis?: boolean;
}

export function MetricCard({label, value, detail, emphasis}: Props): JSX.Element {
    return (
        <article className={`np-metric ${emphasis ? 'is-emphasis' : ''}`}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{detail}</small>
        </article>
    );
}
