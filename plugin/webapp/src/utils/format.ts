export function relativeTime(value: string): string {
    const date = new Date(value);
    const now = Date.now();
    const diffMinutes = Math.max(0, Math.round((now - date.getTime()) / 60_000));
    if (diffMinutes < 1) {
        return 'now';
    }
    if (diffMinutes < 60) {
        return `${diffMinutes}m ago`;
    }
    const hours = Math.round(diffMinutes / 60);
    if (hours < 24) {
        return `${hours}h ago`;
    }
    return `${Math.round(hours / 24)}d ago`;
}

export function percent(value: number): string {
    return `${Math.round(value * 100)}%`;
}

export function humanize(value: string): string {
    return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}
