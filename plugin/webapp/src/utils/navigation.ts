type MattermostWindow = Window & {basename?: string};

function normalizeBase(base: string): string {
    if (!base || base === '/') {
        return '';
    }
    const withLeadingSlash = base.startsWith('/') ? base : `/${base}`;
    return withLeadingSlash.endsWith('/') ? withLeadingSlash.slice(0, -1) : withLeadingSlash;
}

export function sitePath(path: string, source: MattermostWindow = window as MattermostWindow): string {
    const base = normalizeBase(source.basename || '');
    const suffix = path.startsWith('/') ? path : `/${path}`;
    return `${base}${suffix}`;
}

export function teamScopedNoPingPath(source: MattermostWindow = window as MattermostWindow): string {
    const base = normalizeBase(source.basename || '');
    const relativePath = base && source.location.pathname.startsWith(base) ? source.location.pathname.slice(base.length) : source.location.pathname;
    const [teamName] = relativePath.split('/').filter(Boolean);
    return sitePath(teamName ? `/${teamName}/noping` : '/noping', source);
}
