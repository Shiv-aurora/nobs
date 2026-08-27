import React from 'react';

import {CheckIcon} from './icons';

interface Props {
    title: string;
    detail: string;
}

export function EmptyState({title, detail}: Props): JSX.Element {
    return <div className='np-empty'><span><CheckIcon size={24}/></span><h3>{title}</h3><p>{detail}</p></div>;
}
