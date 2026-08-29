import {useEffect} from 'react';

const nativeWorkspace = '/acme/channels/project-atlas';

export function LegacyRedirect(): null {
    useEffect(() => {
        window.location.replace(nativeWorkspace);
    }, []);
    return null;
}
