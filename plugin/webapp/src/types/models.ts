export type Intent = 'factual' | 'live_status' | 'policy' | 'decision' | 'restricted';
export type RunStatus = 'running' | 'answered' | 'escalated' | 'refused' | 'failed';
export type DecisionStatus = 'pending' | 'approved' | 'rejected' | 'discuss';

export interface Availability {
    status: string;
    until: string | null;
    delegate_user_id: string | null;
}

export interface User {
    id: string;
    name: string;
    title: string;
    team_ids: string[];
    roles: string[];
    project_ids: string[];
    availability: Availability;
    avatar: string;
}

export interface Project {
    id: string;
    name: string;
    summary: string;
    owner_user_id: string;
    team_ids: string[];
    status: string;
    health: string;
    blocker_ids: string[];
    target_date: string;
}

export interface Evidence {
    id: string;
    title: string;
    source_type: string;
    source_url: string;
    entity_ids: string[];
    scope: string;
    content: string;
    observed_at: string;
    confidence: number;
    security_state: 'trusted' | 'blocked';
    security_reason?: string | null;
}

export interface RouteStep {
    ordinal: number;
    delegate_id: string;
    delegate_name: string;
    reason: string;
    outcome: string;
    duration_ms: number;
}

export interface SecurityFinding {
    evidence_id: string;
    category: string;
    severity: string;
    reason: string;
    blocked: boolean;
}

export interface QueryResult {
    run_id: string;
    requester_id: string;
    query: string;
    intent: Intent;
    status: RunStatus;
    answer: string;
    headline: string;
    route: RouteStep[];
    evidence: Evidence[];
    confidence: number;
    freshness_label: string;
    people_interrupted: number;
    decision_id?: string | null;
    decision_assignee_id?: string | null;
    policy_result?: string | null;
    security_findings: SecurityFinding[];
    created_at: string;
    completed_at: string;
    cached: boolean;
    model_name?: string | null;
    model_calls: number;
    model_input_tokens: number;
    model_output_tokens: number;
    model_cached_input_tokens: number;
}

export interface DecisionOption {
    id: string;
    label: string;
    tone: 'positive' | 'negative' | 'neutral';
}

export interface Decision {
    id: string;
    canonical_key: string;
    title: string;
    summary: string;
    requester_id: string;
    assignee_id: string;
    project_id?: string | null;
    status: DecisionStatus;
    options: DecisionOption[];
    evidence_ids: string[];
    policy_ids: string[];
    created_at: string;
    due_at?: string | null;
    resolved_at?: string | null;
    resolved_by?: string | null;
    rationale?: string | null;
    handoff_packet_id?: string | null;
}

export interface SemanticWorkState {
    entity_id: string;
    entity_type: 'person' | 'project' | 'team' | 'work_item';
    headline: string;
    detail: string;
    status: string;
    confidence: number;
    source_event_ids: string[];
    updated_at: string;
}

export interface BootstrapResponse {
    organization_id: string;
    current_user: User;
    projects: Project[];
    needs_you: Decision[];
    work_states: SemanticWorkState[];
    attention_metrics: Record<string, number>;
}

export interface Delegate {
    id: string;
    name: string;
    kind: 'personal' | 'project' | 'team' | 'policy' | 'router' | 'authority';
    entity_id: string;
    capabilities: string[];
    data_scopes: string[];
    owner_user_id?: string | null;
    status: string;
}

export interface RegistryResponse {
    delegates: Delegate[];
    relationships: Array<{from: string; type: string; to: string}>;
}

export interface AuditEvent {
    id: string;
    event_type: string;
    actor_id: string;
    entity_ids: string[];
    summary: string;
    created_at: string;
    metadata: Record<string, unknown>;
}


export interface HealthResponse {
    status: string;
    mode: string;
    ai_enabled: boolean;
    version: string;
}

export interface MetricsResponse {
    queries_total: number;
    resolved_without_human: number;
    human_interruptions: number;
    restricted_requests_blocked: number;
    poisoned_sources_blocked: number;
    cache_hits: number;
    model_usage_day: number;
    model_calls: number;
    model_input_tokens: number;
    model_output_tokens: number;
    model_cached_input_tokens: number;
    model_budget_blocks: number;
    active_runs: number;
    delegates: number;
    decision_memories: number;
    meetings_prepared: number;
    meeting_minutes_saved: number;
}

export interface MeetingAttendee {
    user_id: string;
    name: string;
    role: string;
    response_status: 'accepted' | 'tentative' | 'declined' | 'needs_action';
    agent_status: 'ready' | 'consulting' | 'done' | 'skipped';
}

export interface AgendaItem {
    id: string;
    title: string;
    owner_user_id?: string | null;
    status: 'open' | 'resolved' | 'needs_human' | 'skipped';
    resolution?: string | null;
    evidence_ids: string[];
}

export interface AgentTurn {
    id: string;
    ordinal: number;
    agent_name: string;
    agent_kind: 'personal' | 'project' | 'team' | 'policy' | 'authority' | 'integration';
    phase: 'routed' | 'retrieved' | 'work_action' | 'synthesizing' | 'completed';
    conclusion: string;
    evidence_ids: string[];
    open_question?: string | null;
    next_agent?: string | null;
    created_at: string;
}

export interface WorkAction {
    id: string;
    kind: 'github_issue' | 'coding_agent' | 'github_pull_request' | 'calendar_update' | 'message_share';
    provider: string;
    title: string;
    status: 'queued' | 'investigating' | 'testing' | 'blocked' | 'completed';
    summary: string;
    source_url?: string | null;
    workroom_channel?: string | null;
}

export interface MeetingBrief {
    summary: string;
    resolved_items: string[];
    remaining_items: string[];
    proposed_actions: string[];
    recommended_disposition: 'cancel' | 'shorten' | 'keep';
    recommended_duration_minutes: number;
    original_duration_minutes: number;
    minutes_saved: number;
    humans_required: number;
}

export interface MeetingPrepRun {
    id: string;
    meeting_id: string;
    status: string;
    trigger: 'manual' | 'scheduled';
    started_by: string;
    turns: AgentTurn[];
    work_actions: WorkAction[];
    security_findings: SecurityFinding[];
    brief?: MeetingBrief | null;
    created_at: string;
    completed_at?: string | null;
}

export interface Meeting {
    id: string;
    calendar_event_id: string;
    title: string;
    description: string;
    start_at: string;
    end_at: string;
    organizer_user_id: string;
    attendee_user_ids: string[];
    attendees: MeetingAttendee[];
    agenda: AgendaItem[];
    preparation_eligibility: 'eligible' | 'skipped' | 'ambiguous';
    preparation_reason: string;
    preparation_status: 'not_started' | 'running' | 'completed' | 'skipped' | 'stale';
    prep_run_id?: string | null;
    workroom_channel?: string | null;
    etag: string;
    updated_at: string;
    source: 'google_calendar' | 'demo';
    confirmed_action: 'none' | 'cancelled' | 'shortened' | 'agenda_updated';
}

export interface MeetingDetail {
    meeting: Meeting;
    run?: MeetingPrepRun | null;
}
