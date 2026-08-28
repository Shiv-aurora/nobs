import React from 'react';

import logo from '../assets/logo.png';

interface Props {
    title: string;
    detail: string;
}

export function EmptyState({title, detail}: Props): JSX.Element {
    return <div className='np-empty'><span><img src={logo} alt=''/></span><h3>{title}</h3><p>{detail}</p></div>;
}
