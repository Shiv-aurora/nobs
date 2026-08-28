import type {AuditEvent, BootstrapResponse, Decision, HealthResponse, MetricsResponse, QueryResult, RegistryResponse} from '../types/models';
import type {MattermostPost} from '../types/messaging';

const BASE = '/plugins/com.noping.enterprise/api/v1';

export class APIError extends Error {
    public readonly status: number;

    constructor(message: string, status: number) {
        super(message);
        this.status = status;
    }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${BASE}${path}`, {
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            ...(options?.headers || {}),
        },
        ...options,
    });
    const payload = await response.json().catch(() => ({detail: response.statusText}));
    if (!response.ok) {
        throw new APIError(typeof payload.detail === 'string' ? payload.detail : 'Request failed', response.status);
    }
    return payload as T;
}

export const api = {
    health: (): Promise<HealthResponse> => request('/health'),
    bootstrap: (): Promise<BootstrapResponse> => request('/bootstrap'),
    query: (text: string): Promise<QueryResult> => request('/query', {
        method: 'POST',
        body: JSON.stringify({text}),
    }),
    agentReply: (text: string, channelID: string, sourcePostID: string, rootID: string): Promise<{result: QueryResult; post: MattermostPost; message: string}> => request('/messages/agent-reply', {
        method: 'POST',
        body: JSON.stringify({text, channel_id: channelID, source_post_id: sourcePostID, root_id: rootID}),
    }),
    decisions: (): Promise<Decision[]> => request('/decisions'),
    resolveDecision: (decisionID: string, status: string, rationale: string): Promise<unknown> => request(`/decisions/${encodeURIComponent(decisionID)}/resolve`, {
        method: 'POST',
        body: JSON.stringify({status, rationale}),
    }),
    registry: (): Promise<RegistryResponse> => request('/registry'),
    audit: (): Promise<AuditEvent[]> => request('/audit?limit=100'),
    metrics: (): Promise<MetricsResponse> => request('/metrics'),
    resetDemo: (): Promise<{status: string}> => request('/demo/reset', {method: 'POST', body: '{}'}),
};
