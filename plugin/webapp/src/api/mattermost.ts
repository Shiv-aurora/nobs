import type {MattermostChannel, MattermostPost, MattermostPostsResponse, MattermostTeam, MattermostUser, MessagingBootstrap} from '../types/messaging';

export class MattermostAPIError extends Error {
    public readonly status: number;

    constructor(message: string, status: number) {
        super(message);
        this.status = status;
    }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`/api/v4${path}`, {
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            ...(options?.headers || {}),
        },
        ...options,
    });
    const payload = await response.json().catch(() => ({message: response.statusText}));
    if (!response.ok) {
        throw new MattermostAPIError(typeof payload.message === 'string' ? payload.message : 'Mattermost request failed', response.status);
    }
    return payload as T;
}

async function bootstrap(): Promise<MessagingBootstrap> {
    const currentUser = await request<MattermostUser>('/users/me');
    const teams = await request<MattermostTeam[]>(`/users/${encodeURIComponent(currentUser.id)}/teams`);
    if (!teams.length) {
        throw new MattermostAPIError('Your account is not connected to a NoPing workspace yet.', 404);
    }
    const team = teams[0];
    const channels = await request<MattermostChannel[]>(`/users/${encodeURIComponent(currentUser.id)}/teams/${encodeURIComponent(team.id)}/channels`);
    return {currentUser, team, channels};
}

export const mattermost = {
    bootstrap,
    posts: (channelID: string): Promise<MattermostPostsResponse> => request(`/channels/${encodeURIComponent(channelID)}/posts?page=0&per_page=100`),
    users: (ids: string[]): Promise<MattermostUser[]> => ids.length ? request('/users/ids', {method: 'POST', body: JSON.stringify(ids)}) : Promise.resolve([]),
    createPost: (channelID: string, message: string, rootID = ''): Promise<MattermostPost> => request('/posts', {
        method: 'POST',
        body: JSON.stringify({channel_id: channelID, message, root_id: rootID}),
    }),
};
