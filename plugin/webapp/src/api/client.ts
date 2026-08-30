import type {AuditEvent, BootstrapResponse, Decision, HealthResponse, LiveMeetingSession, Meeting, MeetingAgentMode, MeetingDelegation, MeetingDetail, MeetingHandoff, MeetingPrepRun, MetricsResponse, QueryResult, RegistryResponse} from '../types/models';
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
    run: (runID: string): Promise<QueryResult> => request(`/runs/${encodeURIComponent(runID)}`),
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
    meetings: (): Promise<Meeting[]> => request('/meetings'),
    meeting: (meetingID: string): Promise<MeetingDetail> => request(`/meetings/${encodeURIComponent(meetingID)}`),
    prepareMeeting: (meetingID: string): Promise<MeetingPrepRun> => request(`/meetings/${encodeURIComponent(meetingID)}/prepare`, {method: 'POST', body: JSON.stringify({trigger: 'manual'})}),
    confirmMeetingAction: (meetingID: string, action: 'cancel' | 'shorten' | 'update_agenda', expectedETag: string, durationMinutes?: number): Promise<Meeting> => request(`/meetings/${encodeURIComponent(meetingID)}/actions`, {method: 'POST', body: JSON.stringify({action, expected_etag: expectedETag, duration_minutes: durationMinutes})}),
    shareMeeting: (meetingID: string, channelID: string): Promise<unknown> => request(`/meetings/${encodeURIComponent(meetingID)}/share`, {method: 'POST', body: JSON.stringify({channel_id: channelID})}),
    setMeetingAttendance: (meetingID: string, choice: 'attend' | 'agent' | 'decline'): Promise<Meeting> => request(`/meetings/${encodeURIComponent(meetingID)}/attendance`, {method: 'POST', body: JSON.stringify({choice})}),
    createMeetingDelegation: (meetingID: string, mission: {mode: MeetingAgentMode; tell: string[]; ask: string[]; capability_ids: string[]; escalation_rules: string[]}, expectedETag: string): Promise<MeetingDelegation> => request(`/meetings/${encodeURIComponent(meetingID)}/delegations`, {method: 'POST', body: JSON.stringify({...mission, expected_etag: expectedETag})}),
    meetingDelegation: (delegationID: string): Promise<{delegation: MeetingDelegation; session?: LiveMeetingSession | null; handoff?: MeetingHandoff | null; meeting: Meeting}> => request(`/meeting-delegations/${encodeURIComponent(delegationID)}`),
    startMeetingDelegation: (delegationID: string): Promise<{delegation: MeetingDelegation; session: LiveMeetingSession; session_nonce: string}> => request(`/meeting-delegations/${encodeURIComponent(delegationID)}/start`, {method: 'POST', body: '{}'}),
    endMeetingDelegation: (delegationID: string): Promise<MeetingHandoff> => request(`/meeting-delegations/${encodeURIComponent(delegationID)}/end`, {method: 'POST', body: '{}'}),
    revokeMeetingDelegation: (delegationID: string): Promise<MeetingHandoff> => request(`/meeting-delegations/${encodeURIComponent(delegationID)}/revoke`, {method: 'POST', body: '{}'}),
    meetingHandoff: (delegationID: string): Promise<MeetingHandoff> => request(`/meeting-delegations/${encodeURIComponent(delegationID)}/handoff`),
    setOOO: (enabled: boolean, until?: string, delegateUserID?: string): Promise<unknown> => request('/ooo', {method: 'POST', body: JSON.stringify({enabled, until, delegate_user_id: delegateUserID})}),
    oooDigest: (): Promise<{total: number; urgent: number; items: unknown[]}> => request('/ooo/digest'),
    resetDemo: (): Promise<{status: string}> => request('/demo/reset', {method: 'POST', body: '{}'}),
};
